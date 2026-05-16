function toSentenceCase(value) {
  if (!value) return ''
  return value.charAt(0).toUpperCase() + value.slice(1)
}

export function buildIdeaTitle(entry) {
  const normalized = entry?.parsed?.normalized_idea?.trim()
  const category = entry?.parsed?.business_category?.trim()
  const region = entry?.parsed?.region?.trim() || 'Москва'

  if (normalized) {
    return toSentenceCase(normalized)
  }

  if (category) {
    return `${category} (${region})`
  }

  return `Идея #${entry?.id ?? '—'}`
}

export function formatIdeaCreatedAt(value) {
  if (!value) return ''

  return new Date(value).toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
