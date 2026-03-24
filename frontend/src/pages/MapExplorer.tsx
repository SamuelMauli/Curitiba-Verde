import { useEffect, useState, useCallback } from 'react'
import { Map as MapGL, NavigationControl, Source, Layer, Popup } from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'
import { Layers, Pencil, Eye, EyeOff, X, Filter } from 'lucide-react'
import YearSlider from '../components/YearSlider'
import { fetchApi, getImageUrl } from '../hooks/useApi'
import type { MapLayerMouseEvent } from 'react-map-gl/maplibre'
import type { GeoJSON } from 'geojson'

const CURITIBA_CENTER = { longitude: -49.2733, latitude: -25.4284 }

interface PointInfo {
  ndvi?: number
  type?: string
  ndvi_mean?: number
  green_area_ha?: number
  green_percent?: number
}

interface TimelineEvent {
  data: string
  titulo: string
}

interface ClassFilterState {
  vegetation_dense: boolean
  vegetation_light: boolean
  urban: boolean
  bare_soil: boolean
  water: boolean
}

const CLASS_INFO: { key: keyof ClassFilterState; label: string; color: string }[] = [
  { key: 'vegetation_dense', label: 'Vegetação Densa', color: '#22c55e' },
  { key: 'vegetation_light', label: 'Vegetação Leve', color: '#86efac' },
  { key: 'urban', label: 'Área Urbana', color: '#ef4444' },
  { key: 'bare_soil', label: 'Solo Exposto', color: '#eab308' },
  { key: 'water', label: 'Água', color: '#3b82f6' },
]

export default function MapExplorer() {
  const [years, setYears] = useState<number[]>([])
  const [year, setYear] = useState(2023)
  const [layer, setLayer] = useState('ndvi')
  const [bairros, setBairros] = useState<GeoJSON | null>(null)
  const [selectedBairro, setSelectedBairro] = useState<string | null>(null)
  const [popup, setPopup] = useState<{ lat: number; lon: number; info: PointInfo } | null>(null)
  const [showBairros, setShowBairros] = useState(true)
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [drawMode, setDrawMode] = useState(false)
  const [drawnPoints, setDrawnPoints] = useState<[number, number][]>([])
  const [classFilters, setClassFilters] = useState<ClassFilterState>({
    vegetation_dense: true,
    vegetation_light: true,
    urban: true,
    bare_soil: true,
    water: true,
  })

  // Build image URL from layer, year, and active class filters
  const activeClasses = Object.entries(classFilters)
    .filter(([_, v]) => v)
    .map(([k]) => k)
    .join(',')
  const imageUrl = activeClasses.length > 0
    ? getImageUrl(`/api/${layer}/${year}/image?width=800&height=1024&classes=${activeClasses}`)
    : null

  useEffect(() => {
    fetchApi<number[]>('/api/years').then(y => { setYears(y); if (y.length) setYear(y[y.length - 1]) }).catch(console.error)
    fetchApi<GeoJSON>('/api/bairros').then(setBairros).catch(console.error)
  }, [])

  useEffect(() => {
    fetchApi<TimelineEvent[]>(`/api/events?year=${year}&limit=50`).then(setEvents).catch(console.error)
  }, [year])

  const toggleClassFilter = (key: keyof ClassFilterState) => {
    setClassFilters(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const handleMapClick = useCallback(async (e: MapLayerMouseEvent) => {
    if (drawMode) {
      setDrawnPoints(prev => [...prev, [e.lngLat.lng, e.lngLat.lat]])
      return
    }

    // Check if clicked on a bairro
    const features = e.features
    if (features && features.length > 0) {
      const props = features[0].properties
      const name = props?.NOME || props?.nome
      if (name) {
        setSelectedBairro(name as string)
        return
      }
    }

    // Get NDVI value at click point
    try {
      const data = await fetchApi<PointInfo>(`/api/ndvi/${year}/point?lat=${e.lngLat.lat}&lon=${e.lngLat.lng}`)
      if (data.ndvi !== null && data.ndvi !== undefined) {
        setPopup({ lat: e.lngLat.lat, lon: e.lngLat.lng, info: data })
      }
    } catch {
      // ignore click errors
    }
  }, [year, drawMode])

  const finishDrawing = useCallback(() => {
    if (drawnPoints.length >= 3) {
      const polygon = [...drawnPoints, drawnPoints[0]]
      const geojson = {
        type: "Polygon",
        coordinates: [polygon]
      }
      fetchApi<PointInfo>('/api/stats/area', {
        method: 'POST',
        body: JSON.stringify({ geojson, year })
      }).then(stats => {
        setPopup({
          lat: drawnPoints[0][1],
          lon: drawnPoints[0][0],
          info: { ...stats, type: 'area' }
        })
      }).catch(console.error)
    }
    setDrawMode(false)
    setDrawnPoints([])
  }, [drawnPoints, year])

  // Build drawn polygon GeoJSON
  const drawnGeoJSON: GeoJSON.FeatureCollection | null = drawnPoints.length >= 2 ? {
    type: 'FeatureCollection',
    features: [{
      type: 'Feature',
      properties: {},
      geometry: {
        type: 'LineString',
        coordinates: drawnPoints.length >= 3
          ? [...drawnPoints, drawnPoints[0]]
          : drawnPoints
      }
    }]
  } : null

  const drawnPointsGeoJSON: GeoJSON.FeatureCollection | null = drawnPoints.length > 0 ? {
    type: 'FeatureCollection',
    features: drawnPoints.map(([lng, lat]) => ({
      type: 'Feature' as const,
      properties: {},
      geometry: { type: 'Point' as const, coordinates: [lng, lat] }
    }))
  } : null

  return (
    <div style={{ height: '100vh', position: 'relative' }}>
      {/* Map */}
      <MapGL
        initialViewState={{ ...CURITIBA_CENTER, zoom: 11 }}
        style={{ width: '100%', height: '100%' }}
        mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
        onClick={handleMapClick}
        interactiveLayerIds={showBairros && bairros ? ['bairros-fill'] : []}
        cursor={drawMode ? 'crosshair' : 'pointer'}
      >
        <NavigationControl position="bottom-right" />

        {/* NDVI / Layer Overlay */}
        {imageUrl && (
          <Source
            type="image"
            url={imageUrl}
            coordinates={[
              [-49.40, -25.33],
              [-49.15, -25.33],
              [-49.15, -25.65],
              [-49.40, -25.65],
            ]}
          >
            <Layer id="ndvi-overlay" type="raster" paint={{ 'raster-opacity': 0.7 }} />
          </Source>
        )}

        {/* Bairros Layer */}
        {showBairros && bairros && (
          <Source type="geojson" data={bairros}>
            <Layer
              id="bairros-fill"
              type="fill"
              paint={{
                'fill-color': [
                  'case',
                  ['==', ['get', 'NOME'], selectedBairro || ''],
                  'rgba(16, 185, 129, 0.3)',
                  'rgba(16, 185, 129, 0.05)',
                ],
                'fill-outline-color': 'rgba(16, 185, 129, 0.5)',
              }}
            />
            <Layer
              id="bairros-border"
              type="line"
              paint={{
                'line-color': [
                  'case',
                  ['==', ['get', 'NOME'], selectedBairro || ''],
                  '#10B981',
                  'rgba(16, 185, 129, 0.3)',
                ],
                'line-width': [
                  'case',
                  ['==', ['get', 'NOME'], selectedBairro || ''],
                  3,
                  1,
                ],
              }}
            />
            <Layer
              id="bairros-labels"
              type="symbol"
              layout={{
                'text-field': ['get', 'NOME'],
                'text-size': 11,
                'text-anchor': 'center',
              }}
              paint={{
                'text-color': '#d1d5db',
                'text-halo-color': '#000',
                'text-halo-width': 1,
              }}
            />
          </Source>
        )}

        {/* Drawn polygon */}
        {drawnGeoJSON && (
          <Source type="geojson" data={drawnGeoJSON}>
            <Layer
              id="drawn-line"
              type="line"
              paint={{ 'line-color': '#f59e0b', 'line-width': 3, 'line-dasharray': [2, 2] }}
            />
          </Source>
        )}

        {/* Drawn points */}
        {drawnPointsGeoJSON && (
          <Source type="geojson" data={drawnPointsGeoJSON}>
            <Layer
              id="drawn-points"
              type="circle"
              paint={{ 'circle-radius': 5, 'circle-color': '#f59e0b', 'circle-stroke-width': 2, 'circle-stroke-color': '#fff' }}
            />
          </Source>
        )}

        {/* Popup */}
        {popup && (
          <Popup
            latitude={popup.lat}
            longitude={popup.lon}
            onClose={() => setPopup(null)}
            closeButton={true}
            maxWidth="280px"
          >
            <div style={{ color: '#111', padding: 4 }}>
              {popup.info.type === 'area' ? (
                <>
                  <h4 style={{ fontWeight: 700, marginBottom: 4 }}>Área Selecionada</h4>
                  <p>NDVI Médio: <b>{popup.info.ndvi_mean?.toFixed(3)}</b></p>
                  <p>Área verde: <b>{popup.info.green_area_ha?.toFixed(1)} ha</b></p>
                  <p>Cobertura: <b>{popup.info.green_percent?.toFixed(1)}%</b></p>
                </>
              ) : (
                <>
                  <h4 style={{ fontWeight: 700, marginBottom: 4 }}>Ponto</h4>
                  <p>NDVI: <b>{popup.info.ndvi?.toFixed(4)}</b></p>
                  <p>Lat: {popup.lat.toFixed(4)}, Lon: {popup.lon.toFixed(4)}</p>
                </>
              )}
            </div>
          </Popup>
        )}
      </MapGL>

      {/* Sidebar Controls */}
      <div style={{
        position: 'absolute', top: 16, left: 16, width: 280,
        display: 'flex', flexDirection: 'column', gap: 12,
      }}>
        {/* Year Slider */}
        <div className="glass" style={{ padding: 12 }}>
          <YearSlider years={years} value={year} onChange={setYear} />
        </div>

        {/* Layer Toggle */}
        <div className="glass" style={{ padding: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <Layers size={16} color="var(--accent)" />
            <span style={{ fontSize: 13, fontWeight: 600 }}>Camadas</span>
          </div>
          {[
            { id: 'ndvi', label: 'Uso do Solo (NDVI+NDWI+NDBI)' },
            { id: 'classification', label: 'Classificação Multi-Índice' },
            { id: 'change', label: 'Mudança Temporal' },
          ].map(l => (
            <button
              key={l.id}
              onClick={() => setLayer(l.id)}
              style={{
                display: 'block', width: '100%', padding: '6px 10px', marginBottom: 4,
                background: layer === l.id ? 'var(--accent-dim)' : 'transparent',
                border: `1px solid ${layer === l.id ? 'var(--accent)' : 'transparent'}`,
                borderRadius: 6, color: 'var(--text-primary)', cursor: 'pointer',
                fontSize: 13, textAlign: 'left',
              }}
            >
              {l.label}
            </button>
          ))}
        </div>

        {/* Class Filters */}
        {layer === 'ndvi' && (
          <div className="glass" style={{ padding: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <Filter size={16} color="var(--accent)" />
              <span style={{ fontSize: 13, fontWeight: 600 }}>Filtros de Classe</span>
            </div>
            {CLASS_INFO.map(({ key, label, color }) => {
              const active = classFilters[key]
              return (
                <button
                  key={key}
                  onClick={() => toggleClassFilter(key)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8, width: '100%',
                    padding: '6px 10px', marginBottom: 4,
                    background: active ? `${color}18` : 'transparent',
                    border: `1px solid ${active ? `${color}60` : 'rgba(255,255,255,0.1)'}`,
                    borderRadius: 6, cursor: 'pointer', fontSize: 13,
                    color: active ? 'var(--text-primary)' : '#6b7280',
                    opacity: active ? 1 : 0.5,
                    transition: 'all 0.15s ease',
                  }}
                >
                  <span style={{
                    width: 10, height: 10, borderRadius: '50%',
                    background: active ? color : '#4b5563',
                    flexShrink: 0,
                  }} />
                  {label}
                </button>
              )
            })}
          </div>
        )}

        {/* Tools */}
        <div className="glass" style={{ padding: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <Pencil size={16} color="var(--accent)" />
            <span style={{ fontSize: 13, fontWeight: 600 }}>Ferramentas</span>
          </div>
          <button
            onClick={() => { setDrawMode(!drawMode); setDrawnPoints([]) }}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, width: '100%',
              padding: '8px 10px', marginBottom: 4,
              background: drawMode ? 'rgba(245, 158, 11, 0.15)' : 'transparent',
              border: `1px solid ${drawMode ? '#f59e0b' : 'transparent'}`,
              borderRadius: 6, color: drawMode ? '#f59e0b' : 'var(--text-primary)',
              cursor: 'pointer', fontSize: 13,
            }}
          >
            <Pencil size={14} /> {drawMode ? 'Desenhando...' : 'Desenhar Polígono'}
          </button>
          {drawMode && drawnPoints.length >= 3 && (
            <button
              onClick={finishDrawing}
              style={{
                width: '100%', padding: '8px 10px',
                background: '#10B981', border: 'none',
                borderRadius: 6, color: '#fff', cursor: 'pointer',
                fontSize: 13, fontWeight: 600,
              }}
            >
              Calcular Área ({drawnPoints.length} pontos)
            </button>
          )}
          <button
            onClick={() => setShowBairros(!showBairros)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, width: '100%',
              padding: '8px 10px', marginTop: 4,
              background: 'transparent', border: '1px solid transparent',
              borderRadius: 6, color: 'var(--text-primary)', cursor: 'pointer', fontSize: 13,
            }}
          >
            {showBairros ? <Eye size={14} /> : <EyeOff size={14} />}
            {showBairros ? 'Ocultar Bairros' : 'Mostrar Bairros'}
          </button>
        </div>

        {/* Selected Bairro Info */}
        {selectedBairro && (
          <div className="glass" style={{ padding: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h4 style={{ fontSize: 14, fontWeight: 600, color: 'var(--accent)' }}>{selectedBairro}</h4>
              <button
                onClick={() => setSelectedBairro(null)}
                style={{ background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
              ><X size={16} /></button>
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
              Clique no mapa para ver valores NDVI
            </p>
          </div>
        )}

        {/* Events for this year */}
        {events.length > 0 && (
          <div className="glass" style={{ padding: 12, maxHeight: 200, overflow: 'auto' }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
              Eventos em {year} ({events.length})
            </div>
            {events.slice(0, 5).map((e, i) => (
              <div key={i} style={{ padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: 12 }}>
                <span style={{ color: 'var(--text-secondary)' }}>{e.data}</span>
                <br />
                {e.titulo}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Map Legend - bottom right */}
      <div className="glass" style={{
        position: 'absolute', bottom: 32, right: 56, padding: 12,
        minWidth: 160,
      }}>
        <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: 'var(--text-primary)' }}>
          Legenda
        </div>
        {CLASS_INFO.map(({ key, label, color }) => (
          <div key={key} style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '3px 0', fontSize: 11, color: 'var(--text-secondary)',
          }}>
            <span style={{
              width: 12, height: 12, borderRadius: 3,
              background: color, flexShrink: 0,
            }} />
            {label}
          </div>
        ))}
      </div>
    </div>
  )
}
