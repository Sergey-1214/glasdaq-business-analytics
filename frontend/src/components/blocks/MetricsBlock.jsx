import { createElement } from 'react'
import { TrendingUp, DollarSign, Target, Crosshair, Info } from 'lucide-react'
import { useAnalysisStore } from '../../store/analysisStore'
import { useDashboardStore } from '../../store/dashboardStore'
import { buildIdeaTitle, formatIdeaCreatedAt } from '../../utils/ideaPresentation'
import './MetricsBlock.css'

function formatMoney(value) {
  if (!value && value !== 0) return '—'
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)} трлн`
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)} млрд`
  if (value >= 1e6) return `${(value / 1e6).toFixed(0)} млн`
  return Number(value).toLocaleString('ru-RU')
}

const TREND_COLORS = {
  growing: '#4ade80',
  stable: '#facc15',
  declining: '#f87171',
}

const TREND_LABELS = {
  growing: 'Рост',
  stable: 'Стабильный фон',
  declining: 'Снижение',
}

const VERDICT_LABELS = {
  favorable: 'Благоприятный рынок',
  neutral: 'Нейтральный рынок',
  unfavorable: 'Неблагоприятный рынок',
}

function normalizeTrend(trend) {
  if (!trend) return '—'
  return TREND_LABELS[trend] || trend
}

function normalizeVerdict(verdict) {
  if (!verdict) return ''
  return VERDICT_LABELS[verdict] || verdict
}

function trendColor(trend) {
  if (!trend) return '#6b6f80'
  const value = String(trend).toLowerCase()
  if (value.includes('рост') || value.includes('grow') || value.includes('up')) return TREND_COLORS.growing
  if (value.includes('сниж') || value.includes('спад') || value.includes('declin') || value.includes('down')) {
    return TREND_COLORS.declining
  }
  return TREND_COLORS.stable
}

function MetricsEntry({ entry, showVerdict = false }) {
  const { analysis, createdAt } = entry
  const title = buildIdeaTitle(entry)
  const createdAtLabel = formatIdeaCreatedAt(createdAt)

  if (!analysis) {
    return (
      <div className="metrics__entry">
        <div className="metrics__entry-head">
          <div className="metrics__idea">{title}</div>
          {createdAtLabel && <div className="metrics__date">{createdAtLabel}</div>}
        </div>
        <div className="metrics__loading">Анализируется...</div>
      </div>
    )
  }

  const cards = [
    { icon: DollarSign, label: 'TAM', hint: 'Весь рынок', value: formatMoney(analysis.tam), color: '#7c6af5' },
    { icon: Target, label: 'SAM', hint: 'Доступный рынок', value: formatMoney(analysis.sam), color: '#5b8af5' },
    { icon: Crosshair, label: 'SOM', hint: 'Потенциальная доля', value: formatMoney(analysis.som), color: '#4aaef5' },
  ]

  return (
    <div className="metrics__entry">
      <div className="metrics__entry-head">
        <div className="metrics__idea">{title}</div>
        {createdAtLabel && <div className="metrics__date">{createdAtLabel}</div>}
      </div>

      <div className="metrics__cards">
        {cards.map(({ icon, label, hint, value, color }) => (
          <div key={label} className="metrics__card">
            <div className="metrics__card-header">
              {createElement(icon, { size: 13, style: { color } })}
              <span className="metrics__card-label">{label}</span>
              <span className="metrics__card-hint">{hint}</span>
            </div>
            <div className="metrics__card-value" style={{ color }}>
              {value}
            </div>
          </div>
        ))}
      </div>

      <div className="metrics__row">
        <TrendingUp size={13} style={{ color: trendColor(analysis.trend), flexShrink: 0 }} />
        <span className="metrics__trend" style={{ color: trendColor(analysis.trend) }}>
          {normalizeTrend(analysis.trend)}
        </span>
      </div>

      {showVerdict && analysis.verdict && <div className="metrics__verdict">{normalizeVerdict(analysis.verdict)}</div>}
    </div>
  )
}

export default function MetricsBlock() {
  const { entries } = useAnalysisStore()
  const { focusedBlockId } = useDashboardStore()
  const isFocused = focusedBlockId === 'metrics'

  if (!entries.length) {
    return (
      <div className="metrics metrics--empty">
        <Info size={20} className="metrics__empty-icon" />
        <p className="metrics__empty-text">Введите бизнес-идею в ассистенте, и здесь появятся ключевые метрики рынка.</p>
      </div>
    )
  }

  if (!isFocused) {
    return (
      <div className="metrics">
        <MetricsEntry entry={entries[entries.length - 1]} />
      </div>
    )
  }

  return (
    <div className="metrics metrics--focused">
      {[...entries].reverse().map((entry, index) => (
        <div key={entry.id}>
          {index > 0 && <div className="metrics__divider" />}
          <MetricsEntry entry={entry} showVerdict />
        </div>
      ))}
    </div>
  )
}
