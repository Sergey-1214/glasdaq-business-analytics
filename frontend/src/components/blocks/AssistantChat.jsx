import { useState, useRef, useEffect, useMemo } from 'react'
import { Send } from 'lucide-react'
import { prepareWithSegments, layoutWithLines } from '@chenglou/pretext'
import { useDashboardStore } from '../../store/dashboardStore'
import './AssistantChat.css'

const MOCK_RESPONSES = [
  'Анализирую данные рынка. По текущим показателям наблюдается устойчивый рост в секторе технологий — плюс 12% к прошлому кварталу. Рекомендую рассмотреть увеличение инвестиций в этот сегмент.',
  'На основе имеющихся данных: ключевые конкуренты теряют долю рынка на 8% ежеквартально. Сейчас хороший момент для экспансии в освобождающиеся ниши.',
  'Финансовые показатели за период: выручка +23%, EBITDA 18% от выручки, операционные расходы выросли на 7%. Основной резерв роста — оптимизация логистической цепочки.',
  'Анализ аудитории: 67% пользователей — группа 25–34 лет. Конверсия в этом сегменте на 40% выше среднего. Рекомендую перераспределить маркетинговый бюджет в их пользу.',
  'Прогноз на следующий квартал: при текущей динамике выручка составит от 4.2 до 4.8 млн руб. Ключевой риск — волатильность курса и рост стоимости привлечения клиентов.',
  'Слабое место в текущей стратегии — высокая зависимость от одного канала продаж (62% дохода). Диверсификация снизит риски и откроет дополнительные 15–20% выручки.',
  'Добрый день! Я ваш бизнес-ассистент. Могу помочь с анализом рынка, финансовыми показателями или стратегическим планированием. Что вас интересует?',
]

// Конфиг шрифта в зависимости от зоны и режима фокуса
function getFontConfig(focused, zone) {
  if (focused) return { lineHeight: 26, pad: 14, font: '15px Inter, system-ui, sans-serif' }
  if (zone === 'left' || zone === 'bottom') return { lineHeight: 17, pad: 7, font: '11px Inter, system-ui, sans-serif' }
  return { lineHeight: 20, pad: 10, font: '13px Inter, system-ui, sans-serif' }
}

// Рендерит текст ассистента на canvas через pretext.
// Фикс мыльности: учитываем devicePixelRatio для чёткого текста на HiDPI.
function CanvasMessage({ text, fontConfig }) {
  const wrapperRef = useRef(null)
  const canvasRef = useRef(null)
  const timerRef = useRef(null)

  useEffect(() => {
    const wrapper = wrapperRef.current
    const canvas = canvasRef.current
    if (!wrapper || !canvas) return

    clearTimeout(timerRef.current)

    const { font, lineHeight, pad } = fontConfig
    const dpr = window.devicePixelRatio || 1

    document.fonts.ready.then(() => {
      const ctx = canvas.getContext('2d')

      const logicalWidth = wrapper.clientWidth
      const textWidth = logicalWidth - pad * 2

      // pretext: layout без DOM reflow
      const prepared = prepareWithSegments(text, font)
      const { lines, height } = layoutWithLines(prepared, textWidth, lineHeight)

      const logicalHeight = height + pad * 2

      // Физические пиксели = логические × DPR → чёткий текст на ретина
      canvas.width = logicalWidth * dpr
      canvas.height = logicalHeight * dpr
      canvas.style.width = `${logicalWidth}px`
      canvas.style.height = `${logicalHeight}px`

      ctx.scale(dpr, dpr)
      ctx.font = font
      ctx.textBaseline = 'top'

      // Позиции каждого слова в логических пикселях
      const words = []
      for (let li = 0; li < lines.length; li++) {
        const lineWords = lines[li].text.split(' ').filter(Boolean)
        let x = pad
        const y = pad + li * lineHeight
        for (const w of lineWords) {
          words.push({ w, x, y })
          x += ctx.measureText(w + ' ').width
        }
      }

      // Анимация слово за словом
      let idx = 0
      function step() {
        ctx.clearRect(0, 0, logicalWidth, logicalHeight)
        ctx.font = font
        ctx.textBaseline = 'top'
        ctx.fillStyle = '#c8ccd8'

        for (let j = 0; j < idx && j < words.length; j++) {
          ctx.fillText(words[j].w, words[j].x, words[j].y)
        }

        if (idx < words.length) {
          const cur = words[idx]
          ctx.fillStyle = '#7c6af5'
          ctx.fillRect(cur.x, cur.y + 3, 2, lineHeight - 6)
          idx++
          timerRef.current = setTimeout(step, 55)
        }
      }

      step()
    })

    return () => clearTimeout(timerRef.current)
  }, [text, fontConfig])

  return (
    <div ref={wrapperRef} className="canvas-msg">
      <canvas ref={canvasRef} />
    </div>
  )
}

let msgId = 0

export default function AssistantChat() {
  const { focusedBlockId, zones } = useDashboardStore()
  const isFocused = focusedBlockId === 'assistant'
  const zone = Object.entries(zones).find(([, ids]) => ids.includes('assistant'))?.[0] ?? 'right'
  const fontConfig = useMemo(() => getFontConfig(isFocused, zone), [isFocused, zone])

  const [messages, setMessages] = useState([
    { id: ++msgId, role: 'assistant', text: MOCK_RESPONSES[6] },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesRef = useRef(null)

  useEffect(() => {
    const el = messagesRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages])

  function send() {
    const text = input.trim()
    if (!text || loading) return

    setMessages((m) => [...m, { id: ++msgId, role: 'user', text }])
    setInput('')
    setLoading(true)

    const delay = 500 + Math.random() * 700
    setTimeout(() => {
      const response = MOCK_RESPONSES[Math.floor(Math.random() * (MOCK_RESPONSES.length - 1))]
      setMessages((m) => [...m, { id: ++msgId, role: 'assistant', text: response }])
      setLoading(false)
    }, delay)
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className={`chat chat--${zone} ${isFocused ? 'chat--focused' : ''}`}>
      <div className="chat__messages" ref={messagesRef}>
        {messages.map((msg) =>
          msg.role === 'user' ? (
            <div key={msg.id} className="chat__row chat__row--user">
              <div className="chat__bubble chat__bubble--user">{msg.text}</div>
            </div>
          ) : (
            <div key={msg.id} className="chat__row chat__row--assistant">
              <div className="chat__bubble chat__bubble--assistant">
                <CanvasMessage text={msg.text} fontConfig={fontConfig} />
              </div>
            </div>
          )
        )}

        {loading && (
          <div className="chat__row chat__row--assistant">
            <div className="chat__bubble chat__bubble--assistant chat__bubble--typing">
              <span /><span /><span />
            </div>
          </div>
        )}

      </div>

      <div className="chat__input-area" onPointerDown={(e) => e.stopPropagation()}>
        <textarea
          className="chat__input"
          placeholder="Спросите ассистента..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          disabled={loading}
        />
        <button
          className="chat__send"
          onClick={send}
          disabled={!input.trim() || loading}
          title="Отправить"
        >
          <Send size={isFocused ? 17 : 15} />
        </button>
      </div>
    </div>
  )
}
