import { useMemo, useState } from 'react'
import { Download, FileSpreadsheet, FileText, FolderCheck, Info } from 'lucide-react'
import { useAnalysisStore } from '../../store/analysisStore'
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

function buildReportTitle(entry) {
  const normalized = entry.parsed?.normalized_idea?.trim()
  const category = entry.parsed?.business_category?.trim()
  const region = entry.parsed?.region?.trim() || 'Москва'

  if (normalized) {
    return `Отчёт: ${toSentenceCase(normalized)}`
  }

  if (category) {
    return `Отчёт по идее: ${category} (${region})`
  }

  return `Отчёт по идее #${entry.id}`
}

export default function ReportsBlock() {
  const { entries, preparedReports, prepareReport, removePreparedReport } = useAnalysisStore()
  const { focusedBlockId } = useDashboardStore()
  const isFocused = focusedBlockId === 'reports'

  const readyEntries = useMemo(
    () => entries.filter((entry) => entry.analysis).slice().reverse(),
    [entries],
  )

  const preparedEntries = useMemo(
    () => preparedReports
      .map((report) => ({
        ...report,
        entry: entries.find((entry) => entry.id === report.entryId),
      }))
      .filter((report) => report.entry?.analysis)
      .slice()
      .sort((a, b) => new Date(b.generatedAt) - new Date(a.generatedAt)),
    [entries, preparedReports],
  )

  const [selectedEntryId, setSelectedEntryId] = useState(null)

  const effectiveSelectedEntryId = readyEntries.some((entry) => entry.id === selectedEntryId)
    ? selectedEntryId
    : readyEntries[0]?.id ?? null

  const selectedEntry = readyEntries.find((entry) => entry.id === effectiveSelectedEntryId) ?? null
  const selectedPrepared = preparedEntries.find((report) => report.entryId === effectiveSelectedEntryId) ?? null

  function handlePrepareReport() {
    if (!selectedEntry) return
    prepareReport(selectedEntry.id)
  }

  function handleExcel(report) {
    if (!report.entry) return
    downloadExcelReport(report.entry, report.generatedAt)
  }

  function handlePdf(report) {
    if (!report.entry) return
    openPdfReport(report.entry, report.generatedAt)
  }

  if (!readyEntries.length) {
    return (
      <div className="reports reports--empty">
        <Info size={20} className="reports__empty-icon" />
        <p className="reports__empty-text">
          Сначала проанализируйте идею в ассистенте — после этого здесь можно будет подготовить и скачать отчёт.
        </p>
      </div>
    )
  }

  return (
    <div className={`reports ${isFocused ? 'reports--focused' : ''}`}>
      <div className="reports__panel">
        <div className="reports__header">
          <div>
            <div className="reports__title">Конструктор отчёта</div>
            <div className="reports__hint">Выберите идею, подготовьте отчёт и скачайте файл.</div>
          </div>
          <button
            className="reports__prepare-btn"
            onClick={handlePrepareReport}
            disabled={!selectedEntry}
          >
            <FolderCheck size={14} />
            Подготовить отчёт
          </button>
        </div>

        <div className="reports__field">
          <label className="reports__label" htmlFor="reports-idea-select">Подготовленная идея</label>
          <select
            id="reports-idea-select"
            className="reports__select"
            value={effectiveSelectedEntryId ?? ''}
            onChange={(e) => setSelectedEntryId(Number(e.target.value))}
          >
            {readyEntries.map((entry) => (
              <option key={entry.id} value={entry.id}>
                {buildReportTitle(entry)}
              </option>
            ))}
          </select>
        </div>

        {selectedEntry && (
          <div className="reports__summary">
            <div className="reports__summary-title">{buildReportTitle(selectedEntry)}</div>
            <div className="reports__summary-meta">
              <span>TAM: {Number(selectedEntry.analysis.tam).toLocaleString('ru-RU')} ₽</span>
              <span>SAM: {Number(selectedEntry.analysis.sam).toLocaleString('ru-RU')} ₽</span>
              <span>SOM: {Number(selectedEntry.analysis.som).toLocaleString('ru-RU')} ₽</span>
            </div>
            {selectedPrepared ? (
              <div className="reports__status">
                Отчёт готов с {formatPreparedAt(selectedPrepared.generatedAt)}
              </div>
            ) : (
              <div className="reports__status reports__status--muted">
                Эта идея ещё не добавлена в готовые отчёты.
              </div>
            )}
          </div>
        )}
      </div>

      <div className="reports__panel">
        <div className="reports__header reports__header--secondary">
          <div>
            <div className="reports__title">Готовые отчёты</div>
            <div className="reports__hint">Excel скачивается сразу, PDF открывается в печать для сохранения.</div>
          </div>
          <div className="reports__count">{preparedEntries.length}</div>
        </div>

        {!preparedEntries.length ? (
          <div className="reports__empty-prepared">
            <Download size={16} />
            <span>Пока нет подготовленных отчётов.</span>
          </div>
        ) : (
          <div className="reports__list">
            {preparedEntries.map((report) => (
              <div key={report.entryId} className="reports__item">
                <div className="reports__item-main">
                  <div className="reports__item-title">{buildReportTitle(report.entry)}</div>
                  <div className="reports__item-date">{formatPreparedAt(report.generatedAt)}</div>
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
                  <button
                    className="reports__action-btn reports__action-btn--ghost"
                    onClick={() => removePreparedReport(report.entryId)}
                    aria-label="Удалить подготовленный отчёт"
                  >
                    Убрать
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
