import { useEffect, useState, useCallback, useRef } from 'react'
import { Map as MapGL, NavigationControl, Source, Layer, Popup, type MapRef } from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'
import { Layers, Pencil, Eye, EyeOff, X, Filter, Satellite } from 'lucide-react'
import YearSlider from '../components/YearSlider'
import { fetchApi, getImageUrl } from '../hooks/useApi'
import type { MapLayerMouseEvent } from 'react-map-gl/maplibre'
import type { GeoJSON } from 'geojson'

const CURITIBA_CENTER = { longitude: -49.2733, latitude: -25.4284 }

// ── Base map styles ───────────────────────────────────────────────
const BASE_MAPS = {
  dark: {
    label: '🌑 Escuro',
    style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
  },
  satellite: {
    label: '🛰️ Satélite',
    style: {
      version: 8 as const,
      glyphs: 'https://fonts.openmaptiles.org/{fontstack}/{range}.pbf',
      sources: {
        'esri-satellite': {
          type: 'raster' as const,
          tiles: [
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
          ],
          tileSize: 256,
          attribution: '© Esri, Maxar, Earthstar Geographics',
          maxzoom: 19,
        },
        'esri-labels': {
          type: 'raster' as const,
          tiles: [
            'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
          ],
          tileSize: 256,
          maxzoom: 19,
        },
      },
      layers: [
        { id: 'satellite-bg', type: 'raster' as const, source: 'esri-satellite' },
        { id: 'satellite-labels', type: 'raster' as const, source: 'esri-labels', paint: { 'raster-opacity': 0.7 } },
      ],
    },
  },
  streets: {
    label: '🗺️ Ruas',
    style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
  },
}

type BaseMapKey = keyof typeof BASE_MAPS

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

const IMG_COORDS: [[number,number],[number,number],[number,number],[number,number]] = [
  [-49.40, -25.33], [-49.15, -25.33], [-49.15, -25.65], [-49.40, -25.65],
]

function setImgSource(map: any, srcId: string, lyrId: string, url: string | null, opacity: number) {
  try {
    const src = map.getSource(srcId)
    if (!url) {
      // Hide: remove layer+source if they exist
      if (map.getLayer(lyrId)) map.removeLayer(lyrId)
      if (src) map.removeSource(srcId)
      return
    }
    if (src) {
      // Already exists — update image in-place (no remove/add = no race condition)
      src.updateImage({ url, coordinates: IMG_COORDS })
    } else {
      // First time: add source + layer
      map.addSource(srcId, { type: 'image', url, coordinates: IMG_COORDS })
      map.addLayer({
        id: lyrId, type: 'raster', source: srcId,
        paint: { 'raster-opacity': opacity, 'raster-fade-duration': 400 },
      })
    }
  } catch (e) {
    console.error('[setImgSource]', srcId, e)
  }
}

export default function MapExplorer() {
  const mapRef = useRef<MapRef>(null)
  // increments on initial load AND on every style.load (base map switch)
  const [mapReady, setMapReady] = useState(0)
  const [years, setYears] = useState<number[]>([])
  const [year, setYear] = useState(2023)
  const [layer, setLayer] = useState('classification')
  const [baseMap, setBaseMap] = useState<BaseMapKey>('dark')
  const [bairros, setBairros] = useState<GeoJSON | null>(null)
  const [selectedBairro, setSelectedBairro] = useState<string | null>(null)
  const [popup, setPopup] = useState<{ lat: number; lon: number; info: PointInfo } | null>(null)
  const [showBairros, setShowBairros] = useState(true)
  const [showLandsat, setShowLandsat] = useState(false)
  const [showClassification, setShowClassification] = useState(true)
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

  const activeClasses = Object.entries(classFilters)
    .filter(([_, v]) => v)
    .map(([k]) => k)
    .join(',')

  const classificationUrl = showClassification && activeClasses.length > 0
    ? getImageUrl(`/api/classification/${year}/image?width=1024&height=1340&classes=${activeClasses}`)
    : null

  const landsatUrl = getImageUrl(`/api/rgb/${year}/image?width=1024&height=1340`)

  useEffect(() => {
    fetchApi<number[]>('/api/years').then(y => { setYears(y); if (y.length) setYear(y[y.length - 1]) }).catch(console.error)
    fetchApi<GeoJSON>('/api/bairros').then(setBairros).catch(console.error)
  }, [])

  // When switching to satellite mode, automatically show Landsat so the base reflects the selected year
  useEffect(() => {
    if (baseMap === 'satellite') setShowLandsat(true)
  }, [baseMap])

  // Imperatively update MapLibre image sources — deps include the actual URLs so React
  // re-runs whenever year OR visibility changes (no stale closure).
  // mapReady also ensures this re-runs after every base map switch (style.load wipes sources).
  useEffect(() => {
    if (!mapReady) return
    const map = mapRef.current?.getMap()
    if (!map) return
    const isSat = baseMap === 'satellite'
    setImgSource(map, 'landsat-img', 'landsat-layer',
      showLandsat ? landsatUrl : null,
      isSat ? 0.97 : 0.90)
    setImgSource(map, 'classification-img', 'classification-layer',
      classificationUrl,
      showLandsat ? (isSat ? 0.50 : 0.55) : 0.80)
  }, [landsatUrl, classificationUrl, showLandsat, mapReady, baseMap])

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
    const features = e.features
    if (features && features.length > 0) {
      const props = features[0].properties
      const name = props?.NOME || props?.nome
      if (name) { setSelectedBairro(name as string); return }
    }
    try {
      const data = await fetchApi<PointInfo>(`/api/ndvi/${year}/point?lat=${e.lngLat.lat}&lon=${e.lngLat.lng}`)
      if (data.ndvi !== null && data.ndvi !== undefined) {
        setPopup({ lat: e.lngLat.lat, lon: e.lngLat.lng, info: data })
      }
    } catch { /* ignore */ }
  }, [year, drawMode])

  const finishDrawing = useCallback(() => {
    if (drawnPoints.length >= 3) {
      fetchApi<PointInfo>('/api/stats/area', {
        method: 'POST',
        body: JSON.stringify({ geojson: { type: 'Polygon', coordinates: [[...drawnPoints, drawnPoints[0]]] }, year })
      }).then(stats => {
        setPopup({ lat: drawnPoints[0][1], lon: drawnPoints[0][0], info: { ...stats, type: 'area' } })
      }).catch(console.error)
    }
    setDrawMode(false)
    setDrawnPoints([])
  }, [drawnPoints, year])

  const drawnGeoJSON: GeoJSON.FeatureCollection | null = drawnPoints.length >= 2 ? {
    type: 'FeatureCollection',
    features: [{
      type: 'Feature', properties: {},
      geometry: { type: 'LineString', coordinates: drawnPoints.length >= 3 ? [...drawnPoints, drawnPoints[0]] : drawnPoints }
    }]
  } : null

  const drawnPointsGeoJSON: GeoJSON.FeatureCollection | null = drawnPoints.length > 0 ? {
    type: 'FeatureCollection',
    features: drawnPoints.map(([lng, lat]) => ({
      type: 'Feature' as const, properties: {},
      geometry: { type: 'Point' as const, coordinates: [lng, lat] }
    }))
  } : null


  return (
    <div style={{ height: '100vh', position: 'relative' }}>
      {/* Map */}
      <MapGL
        ref={mapRef}
        onLoad={() => {
          setMapReady(n => n + 1)
          const map = mapRef.current?.getMap()
          if (map) {
            map.on('style.load', () => setMapReady(n => n + 1))
          }
        }}
        initialViewState={{ ...CURITIBA_CENTER, zoom: 11 }}
        style={{ width: '100%', height: '100%' }}
        mapStyle={BASE_MAPS[baseMap].style as string}
        onClick={handleMapClick}
        interactiveLayerIds={showBairros && bairros ? ['bairros-fill'] : []}
        cursor={drawMode ? 'crosshair' : 'pointer'}
      >
        <NavigationControl position="bottom-right" />

        {/* Landsat + Classification overlays are managed imperatively via setImgSource() */}

        {/* Bairros borders */}
        {showBairros && bairros && (
          <Source type="geojson" data={bairros}>
            <Layer id="bairros-fill" type="fill" paint={{
              'fill-color': ['case', ['==', ['get', 'NOME'], selectedBairro || ''], 'rgba(16,185,129,0.25)', 'rgba(16,185,129,0.03)'],
              'fill-outline-color': 'rgba(16,185,129,0.4)',
            }} />
            <Layer id="bairros-border" type="line" paint={{
              'line-color': ['case', ['==', ['get', 'NOME'], selectedBairro || ''], '#10B981', 'rgba(16,185,129,0.3)'],
              'line-width': ['case', ['==', ['get', 'NOME'], selectedBairro || ''], 2.5, 0.8],
            }} />
            <Layer id="bairros-labels" type="symbol" layout={{
              'text-field': ['get', 'NOME'], 'text-size': 10, 'text-anchor': 'center',
            }} paint={{
              'text-color': baseMap === 'satellite' ? '#fff' : '#d1d5db',
              'text-halo-color': '#000', 'text-halo-width': 1,
            }} />
          </Source>
        )}

        {drawnGeoJSON && (
          <Source type="geojson" data={drawnGeoJSON}>
            <Layer id="drawn-line" type="line" paint={{ 'line-color': '#f59e0b', 'line-width': 3, 'line-dasharray': [2, 2] }} />
          </Source>
        )}
        {drawnPointsGeoJSON && (
          <Source type="geojson" data={drawnPointsGeoJSON}>
            <Layer id="drawn-points" type="circle" paint={{ 'circle-radius': 5, 'circle-color': '#f59e0b', 'circle-stroke-width': 2, 'circle-stroke-color': '#fff' }} />
          </Source>
        )}

        {popup && (
          <Popup latitude={popup.lat} longitude={popup.lon} onClose={() => setPopup(null)} closeButton maxWidth="280px">
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

      {/* ── Sidebar ─────────────────────────────────────────────── */}
      <div style={{ position: 'absolute', top: 16, left: 16, width: 280, display: 'flex', flexDirection: 'column', gap: 10 }}>

        {/* Year */}
        <div className="glass" style={{ padding: 12 }}>
          <YearSlider years={years} value={year} onChange={setYear} />
        </div>

        {/* Base map switcher */}
        <div className="glass" style={{ padding: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <Satellite size={15} color="var(--accent)" />
            <span style={{ fontSize: 13, fontWeight: 600 }}>Mapa Base</span>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {(Object.keys(BASE_MAPS) as BaseMapKey[]).map(key => (
              <button
                key={key}
                onClick={() => setBaseMap(key)}
                style={{
                  flex: 1, padding: '7px 4px', fontSize: 11, fontWeight: 600,
                  background: baseMap === key ? 'var(--accent-dim)' : 'rgba(255,255,255,0.05)',
                  border: `1.5px solid ${baseMap === key ? 'var(--accent)' : 'rgba(255,255,255,0.1)'}`,
                  borderRadius: 6, color: baseMap === key ? 'var(--accent)' : 'var(--text-secondary)',
                  cursor: 'pointer', transition: 'all 0.15s',
                }}
              >
                {BASE_MAPS[key].label}
              </button>
            ))}
          </div>
        </div>

        {/* Overlay layers */}
        <div className="glass" style={{ padding: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <Layers size={15} color="var(--accent)" />
            <span style={{ fontSize: 13, fontWeight: 600 }}>Camadas de Análise</span>
          </div>

          {/* Landsat toggle */}
          <button
            onClick={() => setShowLandsat(!showLandsat)}
            style={{
              display: 'flex', alignItems: 'center', gap: 8, width: '100%',
              padding: '7px 10px', marginBottom: 5,
              background: showLandsat ? 'rgba(59,130,246,0.15)' : 'rgba(255,255,255,0.04)',
              border: `1px solid ${showLandsat ? '#3b82f6' : 'rgba(255,255,255,0.12)'}`,
              borderRadius: 6, color: showLandsat ? '#60a5fa' : 'var(--text-primary)',
              cursor: 'pointer', fontSize: 13, textAlign: 'left' as const,
            }}
          >
            <span style={{ fontSize: 16 }}>🛰️</span>
            <div>
              <div style={{ fontWeight: 600 }}>
                Satélite Landsat {year}
                {baseMap === 'satellite' && showLandsat && (
                  <span style={{ marginLeft: 6, fontSize: 9, background: '#3b82f6', color: '#fff', borderRadius: 3, padding: '1px 4px' }}>ATIVO</span>
                )}
              </div>
              <div style={{ fontSize: 10, opacity: 0.6 }}>
                {baseMap === 'satellite' ? `Imagem Landsat do ano ${year}` : 'Imagem real do satélite'}
              </div>
            </div>
            <span style={{ marginLeft: 'auto', fontSize: 11, opacity: 0.7 }}>
              {showLandsat ? '✓ ON' : 'OFF'}
            </span>
          </button>

          {/* Classification toggle */}
          <button
            onClick={() => setShowClassification(!showClassification)}
            style={{
              display: 'flex', alignItems: 'center', gap: 8, width: '100%',
              padding: '7px 10px', marginBottom: 5,
              background: showClassification ? 'rgba(34,197,94,0.12)' : 'rgba(255,255,255,0.04)',
              border: `1px solid ${showClassification ? '#22c55e' : 'rgba(255,255,255,0.12)'}`,
              borderRadius: 6, color: showClassification ? '#4ade80' : 'var(--text-primary)',
              cursor: 'pointer', fontSize: 13, textAlign: 'left' as const,
            }}
          >
            <span style={{ fontSize: 16 }}>🎨</span>
            <div>
              <div style={{ fontWeight: 600 }}>Classificação</div>
              <div style={{ fontSize: 10, opacity: 0.6 }}>Uso do solo por classe</div>
            </div>
            <span style={{ marginLeft: 'auto', fontSize: 11, opacity: 0.7 }}>
              {showClassification ? '✓ ON' : 'OFF'}
            </span>
          </button>

          {/* Bairros toggle */}
          <button
            onClick={() => setShowBairros(!showBairros)}
            style={{
              display: 'flex', alignItems: 'center', gap: 8, width: '100%',
              padding: '7px 10px',
              background: showBairros ? 'rgba(16,185,129,0.12)' : 'rgba(255,255,255,0.04)',
              border: `1px solid ${showBairros ? '#10b981' : 'rgba(255,255,255,0.12)'}`,
              borderRadius: 6, color: showBairros ? '#34d399' : 'var(--text-primary)',
              cursor: 'pointer', fontSize: 13, textAlign: 'left' as const,
            }}
          >
            <span style={{ fontSize: 16 }}>🏘️</span>
            <div>
              <div style={{ fontWeight: 600 }}>Limites de Bairros</div>
              <div style={{ fontSize: 10, opacity: 0.6 }}>75 bairros de Curitiba</div>
            </div>
            <span style={{ marginLeft: 'auto', fontSize: 11, opacity: 0.7 }}>
              {showBairros ? '✓ ON' : 'OFF'}
            </span>
          </button>
        </div>

        {/* Class filters (only when classification is on) */}
        {showClassification && (
          <div className="glass" style={{ padding: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <Filter size={15} color="var(--accent)" />
              <span style={{ fontSize: 13, fontWeight: 600 }}>Filtrar Classes</span>
            </div>
            {CLASS_INFO.map(({ key, label, color }) => {
              const active = classFilters[key]
              return (
                <button key={key} onClick={() => toggleClassFilter(key)} style={{
                  display: 'flex', alignItems: 'center', gap: 8, width: '100%',
                  padding: '5px 8px', marginBottom: 3,
                  background: active ? `${color}15` : 'transparent',
                  border: `1px solid ${active ? `${color}50` : 'rgba(255,255,255,0.08)'}`,
                  borderRadius: 5, cursor: 'pointer', fontSize: 12,
                  color: active ? 'var(--text-primary)' : '#6b7280',
                }}>
                  <span style={{ width: 10, height: 10, borderRadius: 3, background: active ? color : '#374151', flexShrink: 0 }} />
                  {label}
                  <span style={{ marginLeft: 'auto', fontSize: 10, opacity: 0.6 }}>{active ? 'ON' : 'OFF'}</span>
                </button>
              )
            })}
          </div>
        )}

        {/* Draw tool */}
        <div className="glass" style={{ padding: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <Pencil size={15} color="var(--accent)" />
            <span style={{ fontSize: 13, fontWeight: 600 }}>Medir Área</span>
          </div>
          <button
            onClick={() => { setDrawMode(!drawMode); setDrawnPoints([]) }}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, width: '100%',
              padding: '8px 10px', marginBottom: drawMode ? 6 : 0,
              background: drawMode ? 'rgba(245,158,11,0.15)' : 'transparent',
              border: `1px solid ${drawMode ? '#f59e0b' : 'rgba(255,255,255,0.12)'}`,
              borderRadius: 6, color: drawMode ? '#f59e0b' : 'var(--text-primary)',
              cursor: 'pointer', fontSize: 13,
            }}
          >
            <Pencil size={14} /> {drawMode ? `Desenhando… (${drawnPoints.length} pts)` : 'Desenhar Polígono'}
          </button>
          {drawMode && drawnPoints.length >= 3 && (
            <button onClick={finishDrawing} style={{
              width: '100%', padding: '8px 10px',
              background: '#10B981', border: 'none',
              borderRadius: 6, color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600,
            }}>
              ✓ Calcular ({drawnPoints.length} pontos)
            </button>
          )}
        </div>

        {/* Events */}
        {events.length > 0 && (
          <div className="glass" style={{ padding: 12, maxHeight: 160, overflow: 'auto' }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: 'var(--accent)' }}>
              📅 Eventos em {year} ({events.length})
            </div>
            {events.slice(0, 4).map((e, i) => (
              <div key={i} style={{ padding: '3px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: 11 }}>
                <span style={{ color: 'var(--text-secondary)' }}>{e.data}</span> — {e.titulo}
              </div>
            ))}
          </div>
        )}

        {selectedBairro && (
          <div className="glass" style={{ padding: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h4 style={{ fontSize: 13, fontWeight: 600, color: 'var(--accent)' }}>{selectedBairro}</h4>
              <button onClick={() => setSelectedBairro(null)} style={{ background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer' }}>
                <X size={15} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="glass" style={{ position: 'absolute', bottom: 32, right: 56, padding: 12, minWidth: 150 }}>
        <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 6, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Legenda
        </div>
        {CLASS_INFO.map(({ key, label, color }) => (
          <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '2px 0', fontSize: 11, color: classFilters[key] ? 'var(--text-primary)' : '#4b5563' }}>
            <span style={{ width: 11, height: 11, borderRadius: 2, background: classFilters[key] ? color : '#374151', flexShrink: 0 }} />
            {label}
          </div>
        ))}
      </div>
    </div>
  )
}
