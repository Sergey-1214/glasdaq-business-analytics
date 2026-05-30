import { useEffect, useMemo, useState } from 'react'
import { Download, FileSpreadsheet, FileText, FolderCheck, Info, Loader2 } from 'lucide-react'
import { apiFetch } from '../../api/client'
import { useAnalysisStore } from '../../store/analysisStore'
import { useAuthStore } from '../../store/authStore'
import { useDashboardStore } from '../../store/dashboardStore'
import { downloadExcelReport, openPdfReport } from '../../utils/reportExport'
import './ReportsBlock.css'

function formatPreparedAt(value) {
  return new Date(value).toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function toSentenceCase(value) {
  if (!value) return ''
  return value.charAt(0).toUpperCase() + value.slice(1)
}

function formatCurrency(value) {
  return Number(value || 0).toLocaleString('ru-RU')
}

function formatSelectedPoint(point) {
  if (!Array.isArray(point) || point.length < 2) {
    return 'не выбрана'
  }

  return `${Number(point[1]).toFixed(6)}, ${Number(point[0]).toFixed(6)}`
}

function buildReportTitle(entry) {
  const normalized = entry.parsed?.normalized_idea?.trim()
  const category = entry.parsed?.business_category?.trim()
  const region = entry.parsed?.region?.trim() || 'Москва'

  if (normalized) {
    return `Отчет: ${toSentenceCase(normalized)}`
  }

  if (category) {
    return `Отчет по идее: ${category} (${region})`
  }

  return `Отчет по идее #${entry.id}`
}

function buildReportPayload(entry) {
  return {
    idea_text: entry.ideaText,
    parsed_payload: entry.parsed,
    analysis_payload: entry.analysis,
    selected_point: entry.selectedPoint
      ? {
          longitude: entry.selectedPoint[0],
          latitude: entry.selectedPoint[1],
        }
      : null,
  }
}

export default function ReportsBlock() {
  const { entries } = useAnalysisStore()
  const { isAuthenticated } = useAuthStore()
  const { focusedBlockId } = useDashboardStore()
  const isFocused = focusedBlockId === 'reports'

  const [reports, setReports] = useState([])
  const [reportsLoading, setReportsLoading] = useState(false)
  const [reportsError, setReportsError] = useState('')
  const [selectedEntryId, setSelectedEntryId] = useState(null)
  const [creatingReportFor, setCreatingReportFor] = useState(null)

  const readyEntries = useMemo(() => entries.filter((entry) => entry.analysis).slice().reverse(), [entries])

  const reportsByIdeaId = useMemo(
    () => new Map(reports.map((report) => [String(report.idea_id), report])),
    [reports],
  )

  const preparedEntries = useMemo(
    () =>
      reports
        .map((report) => ({
          ...report,
          entry: entries.find((entry) => String(entry.id) === String(report.idea_id)),
        }))
        .filter((report) => report.entry?.analysis)
        .slice()
        .sort((a, b) => new Date(b.generated_at) - new Date(a.generated_at)),
    [entries, reports],
  )

  const availableEntries = useMemo(
    () => readyEntries.filter((entry) => !reportsByIdeaId.has(String(entry.id))),
    [readyEntries, reportsByIdeaId],
  )

  const effectiveSelectedEntryId = availableEntries.some((entry) => String(entry.id) === String(selectedEntryId))
    ? selectedEntryId
    : availableEntries[0]?.id ?? null

  const selectedEntry =
    availableEntries.find((entry) => String(entry.id) === String(effectiveSelectedEntryId)) ?? null
  const selectedPrepared = selectedEntry ? reportsByIdeaId.get(String(selectedEntry.id)) ?? null : null
  const selectedEntryPersisted = typeof selectedEntry?.id === 'string'
  const visiblePreparedEntries = isFocused ? preparedEntries : preparedEntries.slice(0, 1)

  useEffect(() => {
    let isCancelled = false

    async function loadReports() {
      if (!isAuthenticated) {
        setReports([])
        setReportsError('')
        return
      }

      setReportsLoading(true)
      setReportsError('')

      try {
        const response = await apiFetch('/api/market/reports/me')
        if (!response.ok) {
          throw new Error(`Failed to load reports: ${response.status}`)
        }

        const payload = await response.json()
        if (!isCancelled) {
          setReports(payload?.data || [])
        }
      } catch (error) {
        if (!isCancelled) {
          console.error('Failed to load reports from backend:', error)
          setReportsError('Не удалось загрузить список отчетов.')
        }
      } finally {
        if (!isCancelled) {
          setReportsLoading(false)
        }
      }
    }

    loadReports()

    return () => {
      isCancelled = true
    }
  }, [isAuthenticated])

  async function handlePrepareReport() {
    if (!selectedEntry || !selectedEntryPersisted) return

    setCreatingReportFor(String(selectedEntry.id))
    setReportsError('')

    try {
      if (selectedPrepared) {
        const response = await apiFetch(`/api/market/reports/${selectedPrepared.id}`, {
          method: 'PATCH',
          body: JSON.stringify({
            format: 'browser-export',
            report_payload: buildReportPayload(selectedEntry),
          }),
        })

        if (!response.ok) {
          throw new Error(`Failed to update report: ${response.status}`)
        }

        const payload = await response.json()
        setReports((currentReports) =>
          currentReports.map((report) => (report.id === payload.data.id ? payload.data : report)),
        )
      } else {
        const response = await apiFetch('/api/market/reports', {
          method: 'POST',
          body: JSON.stringify({
            idea_id: selectedEntry.id,
            format: 'browser-export',
            report_payload: buildReportPayload(selectedEntry),
          }),
        })

        if (!response.ok) {
          throw new Error(`Failed to create report: ${response.status}`)
        }

        const payload = await response.json()
        setReports((currentReports) => [payload.data, ...currentReports])
      }
    } catch (error) {
      console.error('Failed to prepare backend report:', error)
      setReportsError('Не удалось подготовить отчет через сервер.')
    } finally {
      setCreatingReportFor(null)
    }
  }

  function handleExcel(report) {
    if (!report.entry) return
    downloadExcelReport(report.entry, report.generated_at)
  }

  function handlePdf(report) {
    if (!report.entry) return
    openPdfReport(report.entry, report.generated_at)
  }

  if (!readyEntries.length) {
    return (
      <div className="reports reports--empty">
        <Info size={20} className="reports__empty-icon" />
        <p className="reports__empty-text">
          Сначала проанализируйте идею в ассистенте. После этого здесь можно будет подготовить и скачать отчет.
        </p>
      </div>
    )
  }

  return (
    <div className={`reports ${isFocused ? 'reports--focused' : ''}`}>
      <div className="reports__panel">
        <div className="reports__header">
          <div>
            <div className="reports__title">Конструктор отчета</div>
            <div className="reports__hint">Выберите идею, подготовьте отчет на сервере и скачайте файл.</div>
          </div>
          <button
            className="reports__prepare-btn"
            onClick={handlePrepareReport}
            disabled={!selectedEntry || !selectedEntryPersisted || creatingReportFor === String(selectedEntry?.id)}
          >
            {creatingReportFor === String(selectedEntry?.id) ? (
              <Loader2 size={14} className="account__spinner" />
            ) : (
              <FolderCheck size={14} />
            )}
            Подготовить отчет
          </button>
        </div>

        <div className="reports__field">
          <label className="reports__label" htmlFor="reports-idea-select">
            Выбранная идея
          </label>
          <select
            id="reports-idea-select"
            className="reports__select"
            value={effectiveSelectedEntryId ?? ''}
            onChange={(event) => setSelectedEntryId(event.target.value)}
            disabled={!availableEntries.length}
          >
            {!availableEntries.length ? (
              <option value="">Все доступные идеи уже оформлены в отчеты</option>
            ) : (
              availableEntries.map((entry) => (
                <option key={entry.id} value={entry.id}>
                  {buildReportTitle(entry)}
                </option>
              ))
            )}
          </select>
        </div>

        {reportsError && <div className="reports__status reports__status--muted">{reportsError}</div>}

        {selectedEntry ? (
          <div className="reports__summary">
            <div className="reports__summary-title">{buildReportTitle(selectedEntry)}</div>
            <div className="reports__summary-meta">
              <span>TAM: {formatCurrency(selectedEntry.analysis.tam)} ₽</span>
              <span>SAM: {formatCurrency(selectedEntry.analysis.sam)} ₽</span>
              <span>SOM: {formatCurrency(selectedEntry.analysis.som)} ₽</span>
            </div>
            <div className="reports__status reports__status--muted">
              Точка: {formatSelectedPoint(selectedEntry.selectedPoint)}
            </div>
            {!selectedEntryPersisted ? (
              <div className="reports__status reports__status--muted">
                Эту идею пока не удалось сохранить на бэкенде, поэтому отчет для нее недоступен.
              </div>
            ) : selectedPrepared ? (
              <div className="reports__status">Отчет готов с {formatPreparedAt(selectedPrepared.generated_at)}</div>
            ) : (
              <div className="reports__status reports__status--muted">Для этой идеи еще нет серверного отчета.</div>
            )}
          </div>
        ) : (
          <div className="reports__summary">
            <div className="reports__status reports__status--muted">
              Все сохраненные идеи уже имеют подготовленный отчет.
            </div>
          </div>
        )}
      </div>

      <div className="reports__panel">
        <div className="reports__header reports__header--secondary">
          <div>
            <div className="reports__title">Готовые отчеты</div>
            <div className="reports__hint">
              Список хранится на бэкенде. Excel скачивается сразу, PDF открывается в режим печати.
            </div>
          </div>
          <div className="reports__count">{reportsLoading ? '...' : preparedEntries.length}</div>
        </div>

        {reportsLoading ? (
          <div className="reports__empty-prepared">
            <Loader2 size={16} className="account__spinner" />
            <span>Загружаем отчеты...</span>
          </div>
        ) : !preparedEntries.length ? (
          <div className="reports__empty-prepared">
            <Download size={16} />
            <span>Пока нет подготовленных отчетов.</span>
          </div>
        ) : (
          <div className="reports__list">
            {visiblePreparedEntries.map((report) => (
              <div key={report.id} className="reports__item">
                <div className="reports__item-main">
                  <div className="reports__item-title">{buildReportTitle(report.entry)}</div>
                  <div className="reports__item-date">{formatPreparedAt(report.generated_at)}</div>
                  <div className="reports__item-date">Точка: {formatSelectedPoint(report.entry.selectedPoint)}</div>
                </div>
                <div className="reports__item-actions">
                  <button className="reports__action-btn" onClick={() => handleExcel(report)}>
                    <FileSpreadsheet size={14} />
                    Excel
                  </button>
                  <button className="reports__action-btn" onClick={() => handlePdf(report)}>
                    <FileText size={14} />
                    PDF
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
