import { useEffect, useState } from 'react'
import { Map as MapGL, Source, Layer, NavigationControl } from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'
import YearSlider from '../components/YearSlider'
import { fetchApi, getImageUrl } from '../hooks/useApi'

export default function Comparator() {
  const [years, setYears] = useState<number[]>([])
  const [yearA, setYearA] = useState(2000)
  const [yearB, setYearB] = useState(2023)
  const [statsA, setStatsA] = useState<any>(null)
  const [statsB, setStatsB] = useState<any>(null)

  useEffect(() => {
    fetchApi<number[]>('/api/years').then(y => { setYears(y); if (y.length >= 2) { setYearA(y[0]); setYearB(y[y.length - 1]) } }).catch(console.error)
  }, [])

  useEffect(() => {
    fetchApi<any[]>('/api/stats/yearly').then(stats => { setStatsA(stats.find((s: any) => s.year === yearA)); setStatsB(stats.find((s: any) => s.year === yearB)) }).catch(console.error)
  }, [yearA, yearB])

  const ms = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
  const bounds: [[number,number],[number,number],[number,number],[number,number]] = [[-49.40,-25.33],[-49.15,-25.33],[-49.15,-25.65],[-49.40,-25.65]]

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border)' }}>
        <h2 style={{ fontSize: 20, fontWeight: 700 }}>Comparar <span style={{ color: 'var(--accent)' }}>Períodos</span></h2>
      </div>
      <div style={{ flex: 1, display: 'flex' }}>
        <div style={{ flex: 1, position: 'relative', borderRight: '1px solid var(--border)' }}>
          <MapGL initialViewState={{ longitude: -49.2733, latitude: -25.4284, zoom: 11 }} style={{ width: '100%', height: '100%' }} mapStyle={ms}>
            <Source type="image" url={getImageUrl(`/api/ndvi/${yearA}/image`)} coordinates={bounds}><Layer id="a" type="raster" paint={{ 'raster-opacity': 0.7 }} /></Source>
            <NavigationControl position="bottom-right" />
          </MapGL>
          <div className="glass" style={{ position: 'absolute', top: 12, left: 12, padding: 12, minWidth: 200 }}><YearSlider years={years} value={yearA} onChange={setYearA} /></div>
        </div>
        <div style={{ flex: 1, position: 'relative' }}>
          <MapGL initialViewState={{ longitude: -49.2733, latitude: -25.4284, zoom: 11 }} style={{ width: '100%', height: '100%' }} mapStyle={ms}>
            <Source type="image" url={getImageUrl(`/api/ndvi/${yearB}/image`)} coordinates={bounds}><Layer id="b" type="raster" paint={{ 'raster-opacity': 0.7 }} /></Source>
            <NavigationControl position="bottom-right" />
          </MapGL>
          <div className="glass" style={{ position: 'absolute', top: 12, left: 12, padding: 12, minWidth: 200 }}><YearSlider years={years} value={yearB} onChange={setYearB} /></div>
        </div>
      </div>
      {statsA && statsB && (
        <div style={{ padding: 16, borderTop: '1px solid var(--border)', display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 24, alignItems: 'center' }}>
          <div style={{ textAlign: 'center' }}>
            <p style={{ color: 'var(--accent)', fontWeight: 700, fontSize: 24 }}>{yearA}</p>
            <p>NDVI: <b>{statsA.ndvi_mean?.toFixed(3)}</b></p>
            <p>Verde: <b>{statsA.green_percent?.toFixed(1)}%</b></p>
            <p>Área: <b>{statsA.green_area_ha?.toFixed(0)} ha</b></p>
          </div>
          <div style={{ textAlign: 'center' }}>
            <p style={{ fontSize: 32, fontWeight: 700, color: statsB.green_percent < statsA.green_percent ? '#ef4444' : '#10B981' }}>{(statsB.green_percent - statsA.green_percent).toFixed(1)}%</p>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Variação</p>
          </div>
          <div style={{ textAlign: 'center' }}>
            <p style={{ color: 'var(--accent)', fontWeight: 700, fontSize: 24 }}>{yearB}</p>
            <p>NDVI: <b>{statsB.ndvi_mean?.toFixed(3)}</b></p>
            <p>Verde: <b>{statsB.green_percent?.toFixed(1)}%</b></p>
            <p>Área: <b>{statsB.green_area_ha?.toFixed(0)} ha</b></p>
          </div>
        </div>
      )}
    </div>
  )
}
