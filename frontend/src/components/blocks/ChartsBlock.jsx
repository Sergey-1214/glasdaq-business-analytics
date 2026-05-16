import { BarChart2, Info } from 'lucide-react'
import { useAnalysisStore } from '../../store/analysisStore'
import { useDashboardStore } from '../../store/dashboardStore'
import { buildIdeaTitle, formatIdeaCreatedAt } from '../../utils/ideaPresentation'
import './ChartsBlock.css'

const BAR_COLORS = ['#7c6af5', '#5b8af5', '#4aaef5', '#38c4f5', '#2dd4bf', '#34d399']

function fmt(n) {
  if (!n) return '—'
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`
  if (n >= 1e6) return `${(n / 1e6).toFixed(0)}M`
  return String(n)
}

function TamFunnel({ tam, sam, som }) {
  const max = tam || 1
  const bars = [
    { label: 'TAM', value: tam, pct: 100, color: '#7c6af5' },
    { label: 'SAM', value: sam, pct: Math.round((sam / max) * 100), color: '#5b8af5' },
    { label: 'SOM', value: som, pct: Math.round((som / max) * 100), color: '#4aaef5' },
  ]

  return (
    <div className="chart-section">
      <div className="chart-section__title">Размер рынка</div>
      <div className="funnel">
        {bars.map(({ label, value, pct, color }) => (
          <div key={label} className="funnel__row">
            <span className="funnel__label">{label}</span>
            <div className="funnel__track">
              <div className="funnel__bar" style={{ width: `${pct}%`, background: color }} />
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
  const max = Math.max(...competitors.map((item) => item.share), 1)

  return (
    <div className="chart-section">
      <div className="chart-section__title">Конкуренты</div>
      <div className="bars">
        {competitors.map((item, index) => (
          <div key={item.name} className="bars__row">
            <span className="bars__label" title={item.name}>{item.name}</span>
            <div className="bars__track">
              <div
                className="bars__bar"
                style={{
                  width: `${Math.round((item.share / max) * 100)}%`,
                  background: BAR_COLORS[index % BAR_COLORS.length],
                }}
              />
            </div>
            <span className="bars__pct">{item.share}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ChartsEntry({ entry }) {
  const { analysis, createdAt } = entry
  const title = buildIdeaTitle(entry)
  const createdAtLabel = formatIdeaCreatedAt(createdAt)

  if (!analysis) {
    return (
      <div className="charts__entry">
        <div className="charts__entry-head">
          <div className="charts__idea">{title}</div>
          {createdAtLabel && <div className="charts__date">{createdAtLabel}</div>}
        </div>
        <div className="charts__loading">Анализируется...</div>
      </div>
    )
  }

  return (
    <div className="charts__entry">
      <div className="charts__entry-head">
        <div className="charts__idea">{title}</div>
        {createdAtLabel && <div className="charts__date">{createdAtLabel}</div>}
      </div>
      <TamFunnel tam={analysis.tam} sam={analysis.sam} som={analysis.som} />
      <CompetitorsChart competitors={analysis.competitors} />
    </div>
  )
}

export default function ChartsBlock() {
  const { entries } = useAnalysisStore()
  const { focusedBlockId } = useDashboardStore()
  const isFocused = focusedBlockId === 'charts'

  if (!entries.length) {
    return (
      <div className="charts charts--empty">
        <BarChart2 size={20} className="charts__empty-icon" />
        <p className="charts__empty-text">
          Введите бизнес-идею в ассистенте — здесь появятся графики
        </p>
      </div>
    )
  }

  if (!isFocused) {
    return (
      <div className="charts">
        <ChartsEntry entry={entries[entries.length - 1]} />
      </div>
    )
  }

  return (
    <div className="charts charts--focused">
      {[...entries].reverse().map((entry, index) => (
        <div key={entry.id}>
          {index > 0 && <div className="charts__divider" />}
          <ChartsEntry entry={entry} />
        </div>
      ))}
    </div>
  )
}
