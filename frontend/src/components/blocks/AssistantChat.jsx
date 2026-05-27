import { useEffect, useMemo, useRef, useState } from 'react'
import { Send } from 'lucide-react'
import { prepareWithSegments, layoutWithLines } from '@chenglou/pretext'
import { apiFetch } from '../../api/client'
import { useAnalysisStore } from '../../store/analysisStore'
import { useChatStore } from '../../store/chatStore'
import { useDashboardStore } from '../../store/dashboardStore'
import { useLocationStore } from '../../store/locationStore'
import './AssistantChat.css'

const TREND_LABELS = {
  growing: 'рост ↑',
  stable: 'стабильный →',
  declining: 'снижение ↓',
}

const VERDICT_LABELS = {
  favorable: 'Рынок благоприятный — хорошие условия для входа.',
  neutral: 'Рынок нейтральный — возможен вход при правильном позиционировании.',
  unfavorable: 'Рынок неблагоприятный — высокая конкуренция или низкий спрос.',
}

function getFontConfig(focused, zone) {
  if (focused) return { lineHeight: 26, pad: 14, font: '15px Inter, system-ui, sans-serif' }
  if (zone === 'left' || zone === 'bottom') return { lineHeight: 17, pad: 7, font: '11px Inter, system-ui, sans-serif' }
  return { lineHeight: 20, pad: 10, font: '13px Inter, system-ui, sans-serif' }
}

function CanvasAnimation({ id, text, fontConfig }) {
  const markPlayed = useChatStore((state) => state.markPlayed)
  const wrapperRef = useRef(null)
  const canvasRef = useRef(null)
  const timerRef = useRef(null)

  useEffect(() => {
    const wrapper = wrapperRef.current
    const canvas = canvasRef.current
    if (!wrapper || !canvas) return

    const { font, lineHeight, pad } = fontConfig
    const dpr = window.devicePixelRatio || 1

    document.fonts.ready.then(() => {
      const ctx = canvas.getContext('2d')
      const logicalWidth = wrapper.clientWidth
      const textWidth = logicalWidth - pad * 2

      const paragraphs = text.split('\n')
      const words = []
      let offsetY = 0

      canvas.width = logicalWidth * dpr
      canvas.height = dpr
      canvas.style.width = `${logicalWidth}px`
      ctx.scale(dpr, dpr)
      ctx.font = font

      for (const paragraph of paragraphs) {
        if (!paragraph.trim()) {
          offsetY += lineHeight
          continue
        }

        const prepared = prepareWithSegments(paragraph, font)
        const { lines, height } = layoutWithLines(prepared, textWidth, lineHeight)

        for (let lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {
          const lineWords = lines[lineIndex].text.split(' ').filter(Boolean)
          let x = pad
          const y = pad + offsetY + lineIndex * lineHeight

          for (const word of lineWords) {
            words.push({ word, x, y })
            x += ctx.measureText(`${word} `).width
          }
        }

        offsetY += height
      }

      const logicalHeight = offsetY + pad * 2
      canvas.height = logicalHeight * dpr
      canvas.style.height = `${logicalHeight}px`
      ctx.scale(dpr, dpr)
      ctx.font = font
      ctx.textBaseline = 'top'

      let index = 0

      function step() {
        ctx.clearRect(0, 0, logicalWidth, logicalHeight)
        ctx.font = font
        ctx.textBaseline = 'top'
        ctx.fillStyle = '#c8ccd8'

        for (let wordIndex = 0; wordIndex < index && wordIndex < words.length; wordIndex += 1) {
          ctx.fillText(words[wordIndex].word, words[wordIndex].x, words[wordIndex].y)
        }

        if (index < words.length) {
          const currentWord = words[index]
          ctx.fillStyle = '#7c6af5'
          ctx.fillRect(currentWord.x, currentWord.y + 3, 2, lineHeight - 6)
          index += 1
          timerRef.current = setTimeout(step, 55)
        } else {
          markPlayed(id)
        }
      }

      step()
    })

    return () => clearTimeout(timerRef.current)
  }, [fontConfig, id, markPlayed, text])

  return (
    <div ref={wrapperRef} className="canvas-msg">
      <canvas ref={canvasRef} />
    </div>
  )
}

function AssistantText({ text, fontConfig }) {
  const { font, lineHeight, pad } = fontConfig

  return (
    <div
      className="assistant-text"
      style={{ font, lineHeight: `${lineHeight}px`, padding: `${pad}px` }}
    >
      {text}
    </div>
  )
}

function AssistantMessage({ id, text, fontConfig }) {
  const played = useChatStore((state) => state.playedIds.has(id))
  if (played) return <AssistantText text={text} fontConfig={fontConfig} />
  return <CanvasAnimation id={id} text={text} fontConfig={fontConfig} />
}

function formatConfirmation(parsed, hasSelectedPoint) {
  const idea = parsed.normalized_idea || parsed.business_category || 'идея'
  if (hasSelectedPoint) {
    return `Понял: «${idea}». Анализирую рынок и выбранную точку...`
  }
  return `Понял: «${idea}». Анализирую рынок...`
}

function formatMoney(value) {
  if (!value) return '—'
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)} млрд ₽`
  if (value >= 1e6) return `${(value / 1e6).toFixed(0)} млн ₽`
  return `${value.toLocaleString('ru-RU')} ₽`
}

function formatAnalysis(parsed, analysis) {
  const trend = TREND_LABELS[analysis.trend] ?? analysis.trend
  const verdict = VERDICT_LABELS[analysis.verdict] ?? analysis.verdict
  const lines = []

  lines.push(`Объём рынка (${parsed.region || 'Москва'}):`)
  lines.push(`  Весь рынок (TAM): ${formatMoney(analysis.tam)}`)
  lines.push(`  Доступный (SAM): ${formatMoney(analysis.sam)}`)
  lines.push(`  Ваша доля (SOM): ${formatMoney(analysis.som)}`)
  lines.push('')
  lines.push(`Тренд: ${trend}`)

  if (analysis.competitors?.length) {
    const topCompetitors = analysis.competitors
      .slice(0, 3)
      .map((competitor) => `${competitor.name} (${competitor.share}%)`)
      .join(', ')
    lines.push(`Конкуренты: ${topCompetitors}`)
  }

  if (analysis.location_assessment) {
    const location = analysis.location_assessment
    lines.push('')
    lines.push('Оценка выбранной точки:')
    lines.push(`  Координаты: ${location.latitude}, ${location.longitude}`)

    if (location.nearest_competitor_name) {
      lines.push(
        `  Ближайший конкурент: ${location.nearest_competitor_name} (${location.nearest_competitor_distance_m} м)`
      )
    }

    lines.push(
      `  Конкуренция рядом: ${location.competitors_within_500m} в 500 м, ${location.competitors_within_1km} в 1 км`
    )
    lines.push(
      `  Пешеходный трафик: ${location.pedestrian_traffic_estimate?.toLocaleString('ru-RU') || '—'}`
    )
    lines.push(
      `  Средняя аренда: ${location.average_rent_m2?.toLocaleString('ru-RU') || '—'} ₽/м²`
    )
    lines.push(`  Доходность точки: ${location.opportunity_score}/100`)
    lines.push(`  ${location.summary}`)
  }

  lines.push('')
  lines.push(verdict)

  return lines.join('\n')
}

function buildSelectedLocationPayload(selectedPoint) {
  if (!selectedPoint) return {}
  return {
    selected_latitude: selectedPoint[1],
    selected_longitude: selectedPoint[0],
  }
}

export default function AssistantChat() {
  const { focusedBlockId, zones } = useDashboardStore()
  const { messages, loading, addMessage, updateMessage, setLoading } = useChatStore()
  const { addEntry, updateEntryAnalysis } = useAnalysisStore()
  const selectedPoint = useLocationStore((state) => state.selectedPoint)
  const isFocused = focusedBlockId === 'assistant'
  const zone = Object.entries(zones).find(([, ids]) => ids.includes('assistant'))?.[0] ?? 'right'
  const fontConfig = useMemo(() => getFontConfig(isFocused, zone), [isFocused, zone])

  const [input, setInput] = useState('')
  const messagesRef = useRef(null)
  const inputRef = useRef(null)
  const abortRef = useRef(null)

  useEffect(() => {
    const el = messagesRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, loading])

  useEffect(() => {
    const el = inputRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [input])

  async function send() {
    const text = input.trim()
    if (!text || loading) return

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    addMessage('user', text)
    setInput('')
    setLoading(true)

    try {
      const selectedLocationPayload = buildSelectedLocationPayload(selectedPoint)

      const parseRes = await apiFetch('/api/market/api/v1/ideas/parse', {
        method: 'POST',
        body: JSON.stringify({ idea: text, region: 'Москва' }),
        signal: controller.signal,
      })

      if (!parseRes.ok) {
        throw new Error('parse_failed')
      }

      const parseJson = await parseRes.json()
      const parsed = parseJson.data

      if ((parsed.confidence ?? 0) < 0.4) {
        addMessage(
          'assistant',
          'Это не похоже на бизнес-идею. Опишите продукт или услугу чуть конкретнее, и я попробую снова.'
        )
        return
      }

      const ideaText = parsed.normalized_idea || text
      const entryId = addEntry(ideaText, parsed, selectedPoint)
      const confirmId = addMessage('assistant', formatConfirmation(parsed, Boolean(selectedPoint)))

      const analysisRes = await apiFetch('/api/market/api/v1/anal', {
        method: 'POST',
        body: JSON.stringify({
          idea: text,
          region: parsed.region || 'Москва',
          ...selectedLocationPayload,
        }),
        signal: controller.signal,
      })

      if (!analysisRes.ok) {
        throw new Error('anal_failed')
      }

      const analysisJson = await analysisRes.json()
      const analysis = analysisJson.data

      updateEntryAnalysis(entryId, analysis)
      updateMessage(confirmId, formatAnalysis(parsed, analysis))

      try {
        const saveResponse = await apiFetch('/api/market/ideas', {
          method: 'POST',
          body: JSON.stringify({
            idea: text,
            region: parsed.region || 'Москва',
            ...selectedLocationPayload,
            parsed_payload: {
              ...parsed,
              selected_location: selectedPoint
                ? {
                    latitude: selectedPoint[1],
                    longitude: selectedPoint[0],
                  }
                : null,
            },
            analysis_payload: analysis,
          }),
          signal: controller.signal,
        })

        if (!saveResponse.ok) {
          throw new Error('save_failed')
        }
      } catch (saveError) {
        console.error('Failed to persist idea after analysis:', saveError)
        addMessage('assistant', 'Анализ выполнен, но сохранить его в историю пока не удалось.')
      }
    } catch (error) {
      if (error.name === 'AbortError') return

      if (error.message === 'parse_failed') {
        addMessage(
          'assistant',
          'Не удалось распознать идею. Попробуйте описать продукт или услугу чуть подробнее.'
        )
        return
      }

      if (error.message === 'anal_failed') {
        addMessage(
          'assistant',
          'Идея распознана, но анализ рынка сейчас не ответил. Попробуйте повторить запрос чуть позже.'
        )
        return
      }

      addMessage(
        'assistant',
        'Не удалось выполнить анализ. Проверьте подключение к сервису или попробуйте позже.'
      )
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null
      }
      setLoading(false)
    }
  }

  function onKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      send()
    }
  }

  return (
    <div className={`chat chat--${zone} ${isFocused ? 'chat--focused' : ''}`}>
      <div className="chat__messages" ref={messagesRef}>
        {messages.map((message) =>
          message.role === 'user' ? (
            <div key={message.id} className="chat__row chat__row--user">
              <div className="chat__bubble chat__bubble--user">{message.text}</div>
            </div>
          ) : (
            <div key={message.id} className="chat__row chat__row--assistant">
              <div className="chat__bubble chat__bubble--assistant">
                <AssistantMessage id={message.id} text={message.text} fontConfig={fontConfig} />
              </div>
            </div>
          ),
        )}

        {loading && (
          <div className="chat__row chat__row--assistant">
            <div className="chat__bubble chat__bubble--assistant chat__bubble--typing" aria-live="polite">
              <span /><span /><span />
            </div>
          </div>
        )}
      </div>

      <div className="chat__input-area" onPointerDown={(event) => event.stopPropagation()}>
        <textarea
          ref={inputRef}
          className="chat__input"
          placeholder="Опишите бизнес-идею..."
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          disabled={loading}
        />
        <button
          className="chat__send"
          onClick={send}
          disabled={!input.trim() || loading}
          title="Отправить"
          aria-label="Отправить сообщение"
        >
          <Send size={isFocused ? 17 : 15} />
        </button>
      </div>
    </div>
  )
}
