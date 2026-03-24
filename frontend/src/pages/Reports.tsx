import { useEffect, useState } from 'react'
import { fetchApi, getImageUrl } from '../hooks/useApi'
import { FileImage, FileSpreadsheet } from 'lucide-react'

export default function Reports() {
  const [stats, setStats] = useState<any[]>([])
  const [years, setYears] = useState<number[]>([])
  const [sel, setSel] = useState(2023)

  useEffect(() => {
    fetchApi<any[]>('/api/stats/yearly').then(setStats).catch(console.error)
    fetchApi<number[]>('/api/years').then(y => { setYears(y); if (y.length) setSel(y[y.length-1]) }).catch(console.error)
  }, [])

  const dlCSV = () => {
    if (!stats.length) return
    const h = Object.keys(stats[0]); const csv = [h.join(','), ...stats.map(r => h.map(k => r[k]).join(','))].join('\n')
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' })); a.download = 'cwbverde_stats.csv'; a.click()
  }

  return (
    <div style={{ padding: 24, height: '100vh', overflow: 'auto' }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 20 }}><span style={{ color: 'var(--accent)' }}>Relatórios</span></h1>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
        <div className="glass glass-hover" style={{ padding: 20, cursor: 'pointer' }} onClick={dlCSV}>
          <FileSpreadsheet size={32} color="var(--accent)" />
          <h3 style={{ fontSize: 16, fontWeight: 600, marginTop: 12 }}>Exportar CSV</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Dados completos de todos os anos</p>
        </div>
        <div className="glass glass-hover" style={{ padding: 20, cursor: 'pointer' }} onClick={() => window.open(getImageUrl(`/api/ndvi/${sel}/image`), '_blank')}>
          <FileImage size={32} color="#f59e0b" />
          <h3 style={{ fontSize: 16, fontWeight: 600, marginTop: 12 }}>Mapa NDVI {sel}</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Download PNG do mapa</p>
        </div>
      </div>
      <div className="glass" style={{ padding: 16, marginBottom: 24 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Selecionar Ano</h3>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {years.map(y => <button key={y} onClick={() => setSel(y)} style={{ padding: '6px 14px', borderRadius: 6, fontSize: 13, cursor: 'pointer', background: sel === y ? 'var(--accent)' : 'transparent', color: sel === y ? '#fff' : 'var(--text-primary)', border: `1px solid ${sel === y ? 'var(--accent)' : 'var(--border)'}` }}>{y}</button>)}
        </div>
      </div>
      <div className="glass" style={{ padding: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Dados Anuais</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead><tr style={{ borderBottom: '1px solid var(--border)' }}><th style={{ padding: 8, textAlign: 'left' }}>Ano</th><th style={{ padding: 8, textAlign: 'right' }}>NDVI</th><th style={{ padding: 8, textAlign: 'right' }}>Verde (ha)</th><th style={{ padding: 8, textAlign: 'right' }}>Cobertura</th></tr></thead>
          <tbody>{stats.map(s => <tr key={s.year} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}><td style={{ padding: 8, fontWeight: 600 }}>{s.year}</td><td style={{ padding: 8, textAlign: 'right' }}>{s.ndvi_mean?.toFixed(3)}</td><td style={{ padding: 8, textAlign: 'right' }}>{s.green_area_ha?.toFixed(0)}</td><td style={{ padding: 8, textAlign: 'right', color: s.green_percent > 50 ? '#10B981' : '#ef4444' }}>{s.green_percent?.toFixed(1)}%</td></tr>)}</tbody>
        </table>
      </div>
    </div>
  )
}
