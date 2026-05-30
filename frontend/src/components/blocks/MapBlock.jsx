import { useEffect, useRef, useState } from 'react'
import { apiFetch } from '../../api/client'
import { useLocationStore } from '../../store/locationStore'
import './MapBlock.css'

const MAPGL_SCRIPT_ID = 'dgis-mapgl-script'
const MAPGL_SCRIPT_SRC = 'https://mapgl.2gis.com/api/js/v1'
const MOSCOW_CENTER = [37.6176, 55.7558]
const DEFAULT_ZOOM = 11.8
const DEFAULT_REGION = 'Москва'
const DEFAULT_CATEGORY = 'coffee_shop'

function loadMapGlScript() {
  if (window.mapgl) return Promise.resolve(window.mapgl)

  const existingScript = document.getElementById(MAPGL_SCRIPT_ID)
  if (existingScript) {
    if (existingScript.dataset.loadState === 'error') {
      existingScript.remove()
    } else {
      return new Promise((resolve, reject) => {
        existingScript.addEventListener('load', () => resolve(window.mapgl), { once: true })
        existingScript.addEventListener(
          'error',
          () => {
            existingScript.dataset.loadState = 'error'
            reject(new Error('Не удалось загрузить 2GIS MapGL'))
          },
          { once: true },
        )
      })
    }
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.id = MAPGL_SCRIPT_ID
    script.src = MAPGL_SCRIPT_SRC
    script.async = true
    script.onload = () => {
      script.dataset.loadState = 'loaded'
      resolve(window.mapgl)
    }
    script.onerror = () => {
      script.dataset.loadState = 'error'
      reject(new Error('Не удалось загрузить 2GIS MapGL'))
    }
    document.head.appendChild(script)
  })
}

function createMarkerIcon(color, bottomPadding = 0) {
  const height = 44 + bottomPadding
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="34" height="${height}" viewBox="0 0 34 ${height}">
      <path fill="${color}" d="M17 0C8.2 0 1 7.2 1 16.1c0 12 16 27.9 16 27.9s16-15.9 16-27.9C33 7.2 25.8 0 17 0z"/>
      <circle cx="17" cy="16" r="6.2" fill="#ffffff"/>
    </svg>
  `

  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`
}

function formatCoordinates(coordinates) {
  if (!coordinates) return ''
  const [lng, lat] = coordinates
  return `${lat.toFixed(6)}, ${lng.toFixed(6)}`
}

function serializeErrorDetails(value) {
  if (value == null) return ''
  if (typeof value === 'string') return value

  try {
    return JSON.stringify(
      value,
      (_, currentValue) => {
        if (currentValue instanceof Error) {
          return {
            name: currentValue.name,
            message: currentValue.message,
            stack: currentValue.stack,
          }
        }

        if (typeof currentValue === 'object' && currentValue !== null) {
          const plainObject = {}
          for (const key of Object.keys(currentValue)) {
            plainObject[key] = currentValue[key]
          }
          return plainObject
        }

        return currentValue
      },
      2,
    )
  } catch {
    return String(value)
  }
}

function extractMapErrorMessage(errorLike) {
  const details = serializeErrorDetails(errorLike)
  if (!details) {
    return '2GIS вернул пустую ошибку. Проверьте статус ключа и доступ к Map Tiles API.'
  }

  const normalizedDetails = details.toLowerCase()
  if (
    normalizedDetails.includes('invalid key') ||
    normalizedDetails.includes('key is invalid') ||
    normalizedDetails.includes('forbidden') ||
    normalizedDetails.includes('unauthorized')
  ) {
    return 'Ключ 2GIS отклонен. Обычно это значит, что у ключа нет доступа к Map Tiles API или он истек.'
  }

  if (
    normalizedDetails.includes('origin') ||
    normalizedDetails.includes('referer') ||
    normalizedDetails.includes('referrer')
  ) {
    return '2GIS отклонил запрос по ограничению Origin/Referer. Для локальной разработки разрешите localhost и localhost:5173.'
  }

  return details
}

async function parseApiError(response, fallbackMessage) {
  try {
    const json = await response.json()
    if (typeof json?.detail === 'string') return json.detail
    if (typeof json?.message === 'string') return json.message
    if (typeof json?.error === 'string') return json.error
  } catch {
    // Ignore JSON parsing issues for errors.
  }

  return fallbackMessage
}

export default function MapBlock() {
  const apiKey = import.meta.env.VITE_2GIS_API_KEY
  const mapContainerRef = useRef(null)
  const cleanupRef = useRef(() => {})
  const mapRef = useRef(null)
  const mapglRef = useRef(null)
  const selectedMarkerRef = useRef(null)
  const competitorMarkersRef = useRef([])
  const competitorsRef = useRef([])
  const isPickingPointRef = useRef(false)
  const selectedPointRef = useRef(null)
  const selectedPoint = useLocationStore((state) => state.selectedPoint)
  const setSelectedPoint = useLocationStore((state) => state.setSelectedPoint)

  const [status, setStatus] = useState(apiKey ? 'loading' : 'missing-key')
  const [errorMessage, setErrorMessage] = useState('')
  const [errorDetails, setErrorDetails] = useState('')
  const [selectedCompetitor, setSelectedCompetitor] = useState(null)
  const [competitorsCount, setCompetitorsCount] = useState(0)
  const [isPickingPoint, setIsPickingPoint] = useState(false)
  const [showCompetitors, setShowCompetitors] = useState(true)

  function destroyCompetitorMarkers() {
    competitorMarkersRef.current.forEach((marker) => marker.destroy())
    competitorMarkersRef.current = []
  }

  function ensureSelectedMarker(map, mapgl, coordinates = null) {
    if (selectedMarkerRef.current) {
      if (coordinates) {
        selectedMarkerRef.current.setCoordinates(coordinates)
      }
      return selectedMarkerRef.current
    }

    selectedMarkerRef.current = new mapgl.Marker(map, {
      coordinates: coordinates || MOSCOW_CENTER,
      icon: createMarkerIcon('#4fd39a'),
      size: [34, 44],
    })

    return selectedMarkerRef.current
  }

  useEffect(() => {
    isPickingPointRef.current = isPickingPoint
  }, [isPickingPoint])

  useEffect(() => {
    selectedPointRef.current = selectedPoint
  }, [selectedPoint])

  useEffect(() => {
    if (!apiKey) return undefined

    let isDisposed = false

    async function initMap() {
      try {
        setStatus('loading')
        setErrorMessage('')
        setErrorDetails('')

        const response = await apiFetch(
          `/api/market/api/v1/market-points?region=${encodeURIComponent(DEFAULT_REGION)}&category=${encodeURIComponent(DEFAULT_CATEGORY)}&limit=500`,
        )

        if (!response.ok) {
          const detail = await parseApiError(
            response,
            'Не удалось загрузить реальные точки конкурентов из market_service.',
          )
          throw new Error(detail)
        }

        const payload = await response.json()
        competitorsRef.current = (payload?.data || []).map((point) => ({
          id: point.id,
          name: point.name,
          coordinates: [point.longitude, point.latitude],
        }))

        setCompetitorsCount(competitorsRef.current.length)

        const mapgl = await loadMapGlScript()
        if (isDisposed || !mapContainerRef.current) return

        mapglRef.current = mapgl
        const map = new mapgl.Map(mapContainerRef.current, {
          center: MOSCOW_CENTER,
          zoom: DEFAULT_ZOOM,
          key: apiKey,
        })
        mapRef.current = map

        map.on('styleloaderror', (event) => {
          if (isDisposed) return

          const details = serializeErrorDetails(event)
          setStatus('error')
          setErrorMessage(extractMapErrorMessage(event))
          setErrorDetails(details)
          console.error('2GIS styleloaderror:', event)
        })

        map.on('click', (event) => {
          if (isPickingPointRef.current) {
            const nextCoordinates = event.lngLat
            const selectedMarker = ensureSelectedMarker(map, mapgl)

            selectedMarker.setCoordinates(nextCoordinates)
            setSelectedPoint(nextCoordinates)
            setSelectedCompetitor(null)
            setIsPickingPoint(false)
            return
          }

          setSelectedCompetitor(null)
        })

        cleanupRef.current = () => {
          destroyCompetitorMarkers()

          if (selectedMarkerRef.current) {
            selectedMarkerRef.current.destroy()
            selectedMarkerRef.current = null
          }

          map.destroy()
          mapRef.current = null
          mapglRef.current = null
        }

        destroyCompetitorMarkers()

        if (showCompetitors) {
          competitorMarkersRef.current = competitorsRef.current.map((competitor) => {
            const marker = new mapgl.Marker(map, {
              coordinates: competitor.coordinates,
              icon: createMarkerIcon('#ff6b57'),
              size: [34, 44],
            })

            marker.on('click', () => {
              setIsPickingPoint(false)
              setSelectedCompetitor(competitor)
            })

            return marker
          })
        }

        if (selectedPointRef.current) {
          const marker = ensureSelectedMarker(map, mapgl, selectedPointRef.current)
          marker.setCoordinates(selectedPointRef.current)
        }
        setStatus('ready')
      } catch (error) {
        if (!isDisposed) {
          const details = serializeErrorDetails(error)
          setStatus('error')
          setErrorMessage(extractMapErrorMessage(error))
          setErrorDetails(details)
          console.error('2GIS map init error:', error)
        }
      }
    }

    initMap()

    return () => {
      isDisposed = true
      cleanupRef.current()
      cleanupRef.current = () => {}
    }
  }, [apiKey, setSelectedPoint])

  useEffect(() => {
    const map = mapRef.current
    const mapgl = mapglRef.current
    if (!map || !mapgl) return

    destroyCompetitorMarkers()

    if (!showCompetitors) {
      setSelectedCompetitor(null)
      return
    }

    competitorMarkersRef.current = competitorsRef.current.map((competitor) => {
      const marker = new mapgl.Marker(map, {
        coordinates: competitor.coordinates,
        icon: createMarkerIcon('#ff6b57'),
        size: [34, 44],
      })

      marker.on('click', () => {
        setIsPickingPoint(false)
        setSelectedCompetitor(competitor)
      })

      return marker
    })

    if (selectedPointRef.current) {
      const marker = ensureSelectedMarker(map, mapgl, selectedPointRef.current)
      marker.setCoordinates(selectedPointRef.current)
    }
  }, [showCompetitors])

  function handlePickPointToggle() {
    setSelectedCompetitor(null)
    setIsPickingPoint((currentValue) => !currentValue)
  }

  function handleCompetitorsToggle() {
    setShowCompetitors((currentValue) => !currentValue)
  }

  function renderPanelSummary() {
    if (selectedCompetitor) {
      return (
        <div className="map-block__summary">
          <div className="map-block__title">Выбранный конкурент</div>
          <div className="map-block__name">{selectedCompetitor.name}</div>
        </div>
      )
    }

    if (selectedPoint) {
      return (
        <div className="map-block__summary">
          <div className="map-block__title">Ваша будущая точка</div>
          <div className="map-block__coordinates">{formatCoordinates(selectedPoint)}</div>
        </div>
      )
    }

    return (
      <div className="map-block__summary">
        <div className="map-block__title">Ваша будущая точка</div>
        <div className="map-block__hint">Точка еще не выбрана</div>
      </div>
    )
  }

  return (
    <div className="map-block">
      <div className="map-block__canvas" ref={mapContainerRef} />

      {status !== 'ready' && (
        <div className="map-block__overlay">
          {status === 'missing-key' && (
            <>
              <strong>Карта готова к подключению</strong>
              <span>Добавьте `VITE_2GIS_API_KEY` в `.env`, чтобы включить карту Москвы.</span>
            </>
          )}

          {status === 'loading' && (
            <>
              <strong>Загружаем карту Москвы</strong>
              <span>Подтягиваем SDK 2GIS и реальные точки конкурентов из market_service.</span>
            </>
          )}

          {status === 'error' && (
            <>
              <strong>Карта не загрузилась</strong>
              <span>{errorMessage || 'Проверьте API-ключ 2GIS и доступность mapgl.2gis.com.'}</span>
              {errorDetails && <code className="map-block__error-code">{errorDetails}</code>}
            </>
          )}
        </div>
      )}

      <div className="map-block__panel">
        <div className="map-block__legend map-block__legend--compact">
          <span>
            <i className="map-block__legend-dot map-block__legend-dot--selected" />
            Ваша точка
          </span>
          <span>
            <i className="map-block__legend-dot map-block__legend-dot--competitor" />
            {`Конкуренты: ${competitorsCount}`}
          </span>
        </div>

        <button
          className={`map-block__action ${isPickingPoint ? 'map-block__action--active' : ''}`}
          type="button"
          onClick={handlePickPointToggle}
        >
          {isPickingPoint ? 'Отмена выбора' : selectedPoint ? 'Изменить точку' : 'Выбрать точку'}
        </button>

        <button
          className={`map-block__action ${showCompetitors ? 'map-block__action--active' : ''}`}
          type="button"
          onClick={handleCompetitorsToggle}
        >
          {showCompetitors ? 'Скрыть конкурентов' : 'Показать конкурентов'}
        </button>

        {isPickingPoint && (
          <div className="map-block__hint">
            Нажмите на карту, чтобы поставить точку для своей кофейни.
          </div>
        )}

        {renderPanelSummary()}
      </div>
    </div>
  )
}
