import { BarChart2, Info } from 'lucide-react'
import { useAnalysisStore } from '../../store/analysisStore'
import { useDashboardStore } from '../../store/dashboardStore'
import './ChartsBlock.css'

const BAR_COLORS = ['#7c6af5', '#5b8af5', '#4aaef5', '#38c4f5', '#2dd4bf', '#34d399']

function TamFunnel({ tam, sam, som }) {
  const max = tam || 1
  const bars = [
    { label: 'TAM', value: tam, pct: 100, color: '#7c6af5' },
    { label: 'SAM', value: sam, pct: Math.round((sam / max) * 100), color: '#5b8af5' },
    { label: 'SOM', value: som, pct: Math.round((som / max) * 100), color: '#4aaef5' },
  ]

  function fmt(n) {
    if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`
    if (n >= 1e6) return `${(n / 1e6).toFixed(0)}M`
    return String(n)
  }

  return (
    <div className="chart-section">
      <div className="chart-section__title">Размер рынка</div>
      <div className="funnel">
        {bars.map(({ label, value, pct, color }) => (
          <div key={label} className="funnel__row">
            <span className="funnel__label">{label}</span>
            <div className="funnel__track">
              <div
                className="funnel__bar"
                style={{ width: `${pct}%`, background: color }}
              />
            </div>
            <span className="funnel__value">{fmt(value)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function CompetitorsChart({ competitors }) {
  if (!competitors?.length) return null
  const max = Math.max(...competitors.map((c) => c.share), 1)

  return (
    <div className="chart-section">
      <div className="chart-section__title">Конкуренты</div>
      <div className="bars">
        {competitors.map((c, i) => (
          <div key={c.name} className="bars__row">
            <span className="bars__label" title={c.name}>{c.name}</span>
            <div className="bars__track">
              <div
                className="bars__bar"
                style={{
                  width: `${Math.round((c.share / max) * 100)}%`,
                  background: BAR_COLORS[i % BAR_COLORS.length],
                }}
              />
            </div>
            <span className="bars__pct">{c.share}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function ChartsBlock() {
  const { analysis, ideaText } = useAnalysisStore()
  const { focusedBlockId } = useDashboardStore()
  const isFocused = focusedBlockId === 'charts'

  if (!analysis) {
    return (
      <div className="charts charts--empty">
        <BarChart2 size={20} className="charts__empty-icon" />
        <p className="charts__empty-text">Введите бизнес-идею в ассистенте — здесь появятся графики</p>
      </div>
    )
  }

  return (
    <div className={`charts ${isFocused ? 'charts--focused' : ''}`}>
      {ideaText && <div className="charts__idea">{ideaText}</div>}
      <TamFunnel tam={analysis.tam} sam={analysis.sam} som={analysis.som} />
      <div className="charts__divider" />
      <CompetitorsChart competitors={analysis.competitors} />
    </div>
  )
}
