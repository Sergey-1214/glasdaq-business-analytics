const TREND_LABELS = {
  growing: 'Рост',
  stable: 'Стабильный',
  declining: 'Снижение',
}

const VERDICT_LABELS = {
  favorable: 'Благоприятный',
  neutral: 'Нейтральный',
  unfavorable: 'Неблагоприятный',
}

function getPresentationVerdict(analysis) {
  const location = analysis?.location_assessment
  const baseVerdict = analysis?.verdict

  if (!location) return baseVerdict

  const score = Number(location.opportunity_score ?? 0)
  const nearby500m = Number(location.competitors_within_500m ?? 0)
  const nearby1km = Number(location.competitors_within_1km ?? 0)

  if (score < 45 || nearby500m >= 8 || nearby1km >= 40) {
    return 'unfavorable'
  }

  if (score < 65 || nearby500m >= 4 || nearby1km >= 20) {
    return baseVerdict === 'unfavorable' ? 'unfavorable' : 'neutral'
  }

  return baseVerdict
}

function formatCurrency(value) {
  if (!value && value !== 0) return '—'
  return `${Number(value).toLocaleString('ru-RU')} ₽`
}

function formatDateTime(value) {
  return new Date(value).toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatSelectedPoint(selectedPoint) {
  if (!Array.isArray(selectedPoint) || selectedPoint.length < 2) {
    return 'не выбрана'
  }

  return `${Number(selectedPoint[1]).toFixed(6)}, ${Number(selectedPoint[0]).toFixed(6)}`
}

function formatCompetitors(competitors) {
  if (!competitors?.length) {
    return ['—']
  }

  if (competitors.length === 1) {
    return [`${competitors[0].name} — лидер аналитической выборки`]
  }

  return competitors.map((item) => `${item.name}: ${item.share}% веса в выборке`)
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function sanitizeFileName(value) {
  return (
    value
      .toLowerCase()
      .replaceAll(/[^a-zа-я0-9]+/gi, '-')
      .replaceAll(/^-+|-+$/g, '')
      .slice(0, 60) || 'report'
  )
}

function buildReportModel(entry, generatedAt) {
  const { ideaText, parsed, analysis, selectedPoint } = entry
  const presentationVerdict = getPresentationVerdict(analysis)

  return {
    title: ideaText,
    generatedAt,
    category: parsed?.business_category || '—',
    region: parsed?.region || 'Москва',
    subcategory: parsed?.subcategory || '—',
    audience: parsed?.target_audience?.length ? parsed.target_audience.join(', ') : '—',
    selectedPoint: formatSelectedPoint(selectedPoint),
    trend: TREND_LABELS[analysis?.trend] || analysis?.trend || '—',
    verdict: VERDICT_LABELS[presentationVerdict] || presentationVerdict || '—',
    verdictText: presentationVerdict || '—',
    tam: formatCurrency(analysis?.tam),
    sam: formatCurrency(analysis?.sam),
    som: formatCurrency(analysis?.som),
    competitors: formatCompetitors(analysis?.competitors),
  }
}

function createDownload(blob, fileName) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = fileName
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

function buildHtmlDocument(report) {
  const competitorItems = report.competitors.map((item) => `<li>${escapeHtml(item)}</li>`).join('')

  return `<!DOCTYPE html>
<html lang="ru">
  <head>
    <meta charset="utf-8" />
    <title>${escapeHtml(report.title)}</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        margin: 32px;
        color: #1b1d27;
      }
      h1 {
        margin: 0 0 8px;
        font-size: 26px;
      }
      .meta {
        margin-bottom: 24px;
        color: #4c5165;
        font-size: 13px;
      }
      .section {
        margin-bottom: 22px;
      }
      .section-title {
        margin: 0 0 10px;
        font-size: 15px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #444b6a;
      }
      table {
        width: 100%;
        border-collapse: collapse;
      }
      td, th {
        border: 1px solid #d8dce8;
        padding: 10px 12px;
        font-size: 13px;
        text-align: left;
      }
      th {
        background: #eef1f8;
      }
      ul {
        margin: 0;
        padding-left: 20px;
      }
      .verdict {
        padding: 14px 16px;
        background: #f6f8fc;
        border: 1px solid #d8dce8;
      }
      .note {
        margin-top: 10px;
        color: #4c5165;
        font-size: 12px;
      }
    </style>
  </head>
  <body>
    <h1>${escapeHtml(report.title)}</h1>
    <div class="meta">Сформировано: ${escapeHtml(formatDateTime(report.generatedAt))}</div>

    <div class="section">
      <div class="section-title">Параметры идеи</div>
      <table>
        <tr><th>Категория</th><td>${escapeHtml(report.category)}</td></tr>
        <tr><th>Подкатегория</th><td>${escapeHtml(report.subcategory)}</td></tr>
        <tr><th>Регион</th><td>${escapeHtml(report.region)}</td></tr>
        <tr><th>Аудитория</th><td>${escapeHtml(report.audience)}</td></tr>
        <tr><th>Выбранная точка</th><td>${escapeHtml(report.selectedPoint)}</td></tr>
      </table>
    </div>

    <div class="section">
      <div class="section-title">Рыночные метрики</div>
      <table>
        <tr><th>TAM</th><td>${escapeHtml(report.tam)}</td></tr>
        <tr><th>SAM</th><td>${escapeHtml(report.sam)}</td></tr>
        <tr><th>SOM</th><td>${escapeHtml(report.som)}</td></tr>
        <tr><th>Тренд</th><td>${escapeHtml(report.trend)}</td></tr>
      </table>
    </div>

    <div class="section">
      <div class="section-title">Сильные конкуренты в выборке</div>
      <ul>${competitorItems}</ul>
      <div class="note">Проценты отражают относительный вес внутри текущей аналитической выборки, а не долю всего рынка Москвы.</div>
    </div>

    <div class="section">
      <div class="section-title">Вывод</div>
      <div class="verdict">
        <strong>${escapeHtml(report.verdict)}</strong><br />
        ${escapeHtml(report.verdictText)}
      </div>
    </div>
  </body>
</html>`
}

export function downloadExcelReport(entry, generatedAt = new Date().toISOString()) {
  const report = buildReportModel(entry, generatedAt)
  const html = buildHtmlDocument(report)
  const blob = new Blob([`\ufeff${html}`], {
    type: 'application/vnd.ms-excel;charset=utf-8;',
  })

  createDownload(blob, `${sanitizeFileName(report.title)}-report.xls`)
}

export function openPdfReport(entry, generatedAt = new Date().toISOString()) {
  const report = buildReportModel(entry, generatedAt)
  const html = buildHtmlDocument(report)
  const iframe = document.createElement('iframe')
  iframe.style.position = 'fixed'
  iframe.style.right = '0'
  iframe.style.bottom = '0'
  iframe.style.width = '0'
  iframe.style.height = '0'
  iframe.style.border = '0'
  iframe.setAttribute('aria-hidden', 'true')

  document.body.append(iframe)

  const cleanup = () => {
    window.setTimeout(() => {
      iframe.remove()
    }, 1000)
  }

  const printFrame = () => {
    const frameWindow = iframe.contentWindow
    if (!frameWindow) {
      cleanup()
      return
    }

    frameWindow.focus()
    frameWindow.print()
    cleanup()
  }

  iframe.onload = () => {
    window.setTimeout(printFrame, 150)
  }

  const frameDocument = iframe.contentDocument
  if (!frameDocument) {
    cleanup()
    return false
  }

  frameDocument.open()
  frameDocument.write(html)
  frameDocument.close()
  return true
}
