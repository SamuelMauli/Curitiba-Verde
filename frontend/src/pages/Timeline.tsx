import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { fetchApi } from '../hooks/useApi'
import { Search } from 'lucide-react'

const CC: Record<string, string> = {
  legislacao: '#1565C0', parque_area_verde: '#2E7D32', obra_infraestrutura: '#F44336',
  empreendimento: '#FF9800', desastre_ambiental: '#B71C1C', politica_publica: '#7B1FA2',
  licenciamento: '#FF6F00', transporte: '#00838F', demografico: '#546E7A', educacao_cultura: '#4527A0',
}
const CL: Record<string, string> = {
  legislacao: 'Legislação', parque_area_verde: 'Parques', obra_infraestrutura: 'Obras',
  empreendimento: 'Empreendimentos', desastre_ambiental: 'Desastres', politica_publica: 'Políticas',
  licenciamento: 'Licenciamento', transporte: 'Transporte', demografico: 'Demografia', educacao_cultura: 'Educação',
}

export default function Timeline() {
  const [events, setEvents] = useState<any[]>([])
  const [filter, setFilter] = useState('')
  const [catF, setCatF] = useState<string | null>(null)
  const [yearF, setYearF] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    let url = '/api/events?limit=2000'
    if (yearF) url += `&year=${yearF}`
    if (catF) url += `&category=${catF}`
    fetchApi<any[]>(url).then(d => { setEvents(d); setLoading(false) }).catch(console.error)
  }, [yearF, catF])

  const filtered = events.filter(e => !filter || e.titulo?.toLowerCase().includes(filter.toLowerCase()) || e.descricao?.toLowerCase().includes(filter.toLowerCase()))
  const byYear: Record<string, any[]> = {}
  filtered.forEach(e => { const y = e.data?.substring(0, 4) || '?'; if (!byYear[y]) byYear[y] = []; byYear[y].push(e) })

  return (
    <div style={{ height: '100vh', overflow: 'auto', padding: 24 }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 4 }}>Timeline <span style={{ color: 'var(--accent)' }}>Histórica</span></h1>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 20 }}>{events.length} eventos documentados</p>
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
          <Search size={16} style={{ position: 'absolute', left: 12, top: 10, color: '#6b7280' }} />
          <input placeholder="Buscar eventos..." value={filter} onChange={e => setFilter(e.target.value)} style={{ width: '100%', padding: '8px 12px 8px 36px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)', fontSize: 14, outline: 'none' }} />
        </div>
        <select value={catF || ''} onChange={e => setCatF(e.target.value || null)} style={{ padding: '8px 12px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)', fontSize: 14 }}>
          <option value="">Todas categorias</option>
          {Object.entries(CL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={yearF || ''} onChange={e => setYearF(e.target.value ? Number(e.target.value) : null)} style={{ padding: '8px 12px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)', fontSize: 14 }}>
          <option value="">Todos os anos</option>
          {Array.from({ length: 27 }, (_, i) => 2000 + i).map(y => <option key={y} value={y}>{y}</option>)}
        </select>
      </div>
      <div style={{ display: 'flex', gap: 6, marginBottom: 20, flexWrap: 'wrap' }}>
        {Object.entries(CC).map(([cat, color]) => (
          <button key={cat} onClick={() => setCatF(catF === cat ? null : cat)} style={{ padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 500, background: catF === cat ? color : `${color}20`, color: catF === cat ? '#fff' : color, border: `1px solid ${color}50`, cursor: 'pointer' }}>{CL[cat]}</button>
        ))}
      </div>
      {loading ? <p style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary)' }}>Carregando...</p> : (
        <div style={{ position: 'relative', paddingLeft: 30 }}>
          <div style={{ position: 'absolute', left: 14, top: 0, bottom: 0, width: 2, background: 'var(--border)' }} />
          {Object.entries(byYear).sort(([a], [b]) => b.localeCompare(a)).map(([year, ye]) => (
            <div key={year} style={{ marginBottom: 24 }}>
              <div style={{ position: 'relative', marginBottom: 12 }}>
                <div style={{ position: 'absolute', left: -24, top: 2, width: 12, height: 12, borderRadius: '50%', background: 'var(--accent)', border: '2px solid var(--bg-primary)' }} />
                <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--accent)' }}>{year} <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--text-secondary)' }}>({ye.length})</span></h3>
              </div>
              {ye.map((ev: any, i: number) => (
                <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: Math.min(i * 0.015, 0.3) }} className="glass glass-hover" style={{ padding: 12, marginBottom: 8, marginLeft: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ padding: '2px 8px', borderRadius: 10, fontSize: 10, fontWeight: 600, background: `${CC[ev.categoria] || '#666'}20`, color: CC[ev.categoria] || '#666' }}>{CL[ev.categoria] || ev.categoria}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{ev.data}</span>
                    {ev.impacto_ndvi === 'positivo' && <span style={{ color: '#10B981' }}>↑</span>}
                    {ev.impacto_ndvi === 'negativo' && <span style={{ color: '#ef4444' }}>↓</span>}
                  </div>
                  <h4 style={{ fontSize: 14, fontWeight: 600 }}>{ev.titulo}</h4>
                  {ev.descricao && <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.4 }}>{ev.descricao}</p>}
                </motion.div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
