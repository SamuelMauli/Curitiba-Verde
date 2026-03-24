import { useEffect, useState } from 'react'
import { fetchApi, getImageUrl } from '../hooks/useApi'
import { FileImage, FileSpreadsheet, TrendingDown, TreePine, BarChart3 } from 'lucide-react'

export default function Reports() {
  const [stats, setStats] = useState<any[]>([])
  const [years, setYears] = useState<number[]>([])
  const [sel, setSel] = useState(2023)

  useEffect(() => {
    fetchApi<any[]>('/api/stats/yearly').then(setStats).catch(console.error)
    fetchApi<number[]>('/api/years').then(y => { setYears(y); if (y.length) setSel(y[y.length-1]) }).catch(console.error)
  }, [])

  const latest = stats[stats.length - 1]
  const first = stats[0]
  const ndviChange = first && latest ? ((latest.ndvi_mean - first.ndvi_mean) / first.ndvi_mean * 100) : 0
  const greenChange = first && latest ? (latest.green_percent - first.green_percent) : 0

  const dlCSV = () => {
    if (!stats.length) return
    const h = Object.keys(stats[0]); const csv = [h.join(','), ...stats.map(r => h.map(k => r[k]).join(','))].join('\n')
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' })); a.download = 'cwbverde_stats.csv'; a.click()
  }

  return (
    <div style={{ padding: 24, height: '100vh', overflow: 'auto' }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 20 }}><span style={{ color: 'var(--accent)' }}>Relatórios</span></h1>

      {/* Resumo Geral */}
      {latest && first && (
        <div className="glass" style={{ padding: 20, marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16, color: 'var(--accent)' }}>Resumo Geral</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(16,185,129,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <TreePine size={20} color="#10B981" />
              </div>
              <div>
                <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Cobertura Atual</p>
                <p style={{ fontSize: 20, fontWeight: 700, color: '#10B981' }}>{latest.green_percent.toFixed(1)}%</p>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(245,158,11,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <TrendingDown size={20} color="#f59e0b" />
              </div>
              <div>
                <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>NDVI Médio Atual</p>
                <p style={{ fontSize: 20, fontWeight: 700, color: '#f59e0b' }}>{latest.ndvi_mean.toFixed(3)}</p>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: `rgba(${greenChange >= 0 ? '16,185,129' : '239,68,68'},0.15)`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <BarChart3 size={20} color={greenChange >= 0 ? '#10B981' : '#ef4444'} />
              </div>
              <div>
                <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Variação {first.year}–{latest.year}</p>
                <p style={{ fontSize: 20, fontWeight: 700, color: greenChange >= 0 ? '#10B981' : '#ef4444' }}>
                  {greenChange >= 0 ? '+' : ''}{greenChange.toFixed(1)}% cobertura
                </p>
                <p style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                  NDVI: {ndviChange >= 0 ? '+' : ''}{ndviChange.toFixed(1)}%
                </p>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(6,182,212,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <FileSpreadsheet size={20} color="#06b6d4" />
              </div>
              <div>
                <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Período Analisado</p>
                <p style={{ fontSize: 20, fontWeight: 700, color: '#06b6d4' }}>{stats.length} anos</p>
                <p style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{first.year} a {latest.year}</p>
              </div>
            </div>
          </div>
        </div>
      )}

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
