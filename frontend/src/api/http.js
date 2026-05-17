export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function parseJsonSafely(response) {
  try {
    return await response.json()
  } catch {
    return null
  }
}

export async function parseApiResponse(response, fallbackError) {
  const json = await parseJsonSafely(response)

  if (!response.ok) {
    const detail = json?.detail
    if (Array.isArray(detail)) {
      throw new Error(detail[0]?.msg || fallbackError)
    }
    throw new Error(typeof detail === 'string' ? detail : fallbackError)
  }

  return json?.data
}
