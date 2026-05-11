import { TrendingUp, DollarSign, Target, Crosshair, Info } from 'lucide-react'
import { useAnalysisStore } from '../../store/analysisStore'
import { useDashboardStore } from '../../store/dashboardStore'
import './MetricsBlock.css'

function fmtMoney(n) {
  if (!n && n !== 0) return '—'
  if (n >= 1e12) return `${(n / 1e12).toFixed(1)} трлн`
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)} млрд`
  if (n >= 1e6) return `${(n / 1e6).toFixed(0)} млн`
  return n.toLocaleString('ru-RU')
}

const TREND_COLORS = {
  growing: '#4ade80',
  stable: '#facc15',
  declining: '#f87171',
}

function trendColor(trend) {
  if (!trend) return '#6b6f80'
  const t = trend.toLowerCase()
  if (t.includes('рост') || t.includes('grow') || t.includes('up')) return TREND_COLORS.growing
  if (t.includes('спад') || t.includes('declin') || t.includes('down')) return TREND_COLORS.declining
  return TREND_COLORS.stable
}

function MetricsEntry({ entry, showVerdict = false }) {
  const { ideaText, analysis } = entry

  if (!analysis) {
    return (
      <div className="metrics__entry">
        {ideaText && <div className="metrics__idea">{ideaText}</div>}
        <div className="metrics__loading">Анализируется...</div>
      </div>
    )
  }

  const cards = [
    { icon: DollarSign, label: 'TAM', hint: 'Весь рынок',    value: fmtMoney(analysis.tam), color: '#7c6af5' },
    { icon: Target,     label: 'SAM', hint: 'Доступный',     value: fmtMoney(analysis.sam), color: '#5b8af5' },
    { icon: Crosshair,  label: 'SOM', hint: 'Реалистичный',  value: fmtMoney(analysis.som), color: '#4aaef5' },
  ]

  return (
    <div className="metrics__entry">
      {ideaText && <div className="metrics__idea">{ideaText}</div>}
      <div className="metrics__cards">
        {cards.map(({ icon: Icon, label, hint, value, color }) => (
          <div key={label} className="metrics__card">
            <div className="metrics__card-header">
              <Icon size={13} style={{ color }} />
              <span className="metrics__card-label">{label}</span>
              <span className="metrics__card-hint">{hint}</span>
            </div>
            <div className="metrics__card-value" style={{ color }}>{value}</div>
          </div>
        ))}
      </div>
      <div className="metrics__row">
        <TrendingUp size={13} style={{ color: trendColor(analysis.trend), flexShrink: 0 }} />
        <span className="metrics__trend" style={{ color: trendColor(analysis.trend) }}>
          {analysis.trend}
        </span>
      </div>
      {showVerdict && analysis.verdict && (
        <div className="metrics__verdict">{analysis.verdict}</div>
      )}
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
        <p className="metrics__empty-text">Введите бизнес-идею в ассистенте — здесь появятся метрики рынка</p>
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
      {[...entries].reverse().map((entry, i) => (
        <div key={entry.id}>
          {i > 0 && <div className="metrics__divider" />}
          <MetricsEntry entry={entry} showVerdict />
        </div>
      ))}
    </div>
  )
}
