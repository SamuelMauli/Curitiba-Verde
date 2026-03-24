import { useEffect, useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { TreePine, TrendingDown, MapPin, Calendar, ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, CartesianGrid, Cell, ReferenceLine } from 'recharts'
import StatCard from '../components/StatCard'
import { fetchApi } from '../hooks/useApi'

interface YearlyStat {
  year: number
  ndvi_mean: number
  green_area_ha: number
  green_percent: number
}

interface EventStats {
  total: number
}

export default function Dashboard() {
  const [stats, setStats] = useState<YearlyStat[]>([])
  const [eventStats, setEventStats] = useState<EventStats | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetchApi<YearlyStat[]>('/api/stats/yearly').then(setStats).catch(console.error)
    fetchApi<EventStats>('/api/events/stats').then(setEventStats).catch(console.error)
  }, [])

  const latest = stats[stats.length - 1]
  const first = stats[0]
  const trend = first && latest
    ? ((latest.green_percent - first.green_percent) / first.green_percent) * 100
    : 0

  const variationData = useMemo(() => {
    if (stats.length < 2) return []
    return stats.slice(1).map((s, i) => ({
      year: s.year,
      delta: Number(((s.ndvi_mean - stats[i].ndvi_mean) * 100).toFixed(2)),
    }))
  }, [stats])

  return (
    <div style={{ padding: 24, height: '100vh', overflow: 'auto' }}>
      {/* Header */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 4 }}>
          <span style={{ color: 'var(--accent)' }}>CwbVerde</span> Dashboard
        </h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Mapeamento de desmatamento de Curitiba — 2000 a 2023
        </p>
      </motion.div>

      {/* Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginBottom: 24 }}>
        <StatCard
          title="Cobertura Vegetal Atual"
          value={latest ? `${latest.green_percent.toFixed(1)}%` : '—'}
          subtitle={latest ? `${latest.green_area_ha.toFixed(0)} hectares` : ''}
          icon={TreePine}
          trend={trend}
        />
        <StatCard
          title="NDVI Médio"
          value={latest ? latest.ndvi_mean.toFixed(3) : '—'}
          subtitle="Índice de vegetação"
          icon={TrendingDown}
          color="#f59e0b"
        />
        <StatCard
          title="Eventos Históricos"
          value={eventStats ? String(eventStats.total) : '—'}
          subtitle="Marcos urbanos documentados"
          icon={Calendar}
          color="#8b5cf6"
        />
        <StatCard
          title="Bairros Monitorados"
          value="30+"
          subtitle="Cobertura completa"
          icon={MapPin}
          color="#06b6d4"
        />
      </div>

      {/* Charts - Row 1: two columns */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
        {/* NDVI Time Series */}
        <div className="glass" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Evolução do NDVI</h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={stats}>
              <defs>
                <linearGradient id="ndviGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="year" stroke="#6b7280" fontSize={12} />
              <YAxis stroke="#6b7280" fontSize={12} domain={['auto', 'auto']} />
              <Tooltip
                contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, color: '#f3f4f6' }}
                formatter={(value: number) => [`${value.toFixed(4)}`, 'NDVI']}
                labelFormatter={(label) => `Ano: ${label}`}
              />
              <Area type="monotone" dataKey="ndvi_mean" stroke="#10B981" fill="url(#ndviGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Green Area Bar Chart */}
        <div className="glass" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Área Verde (hectares)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={stats}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="year" stroke="#6b7280" fontSize={12} />
              <YAxis stroke="#6b7280" fontSize={12} />
              <Tooltip
                contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, color: '#f3f4f6' }}
                formatter={(value: number) => [`${value.toFixed(0)} ha`, 'Área Verde']}
                labelFormatter={(label) => `Ano: ${label}`}
              />
              <Bar dataKey="green_area_ha" fill="#10B981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts - Row 2: full width variation chart */}
      <div style={{ marginBottom: 24 }}>
        <div className="glass" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Variação Anual do NDVI (%)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={variationData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="year" stroke="#6b7280" fontSize={12} />
              <YAxis stroke="#6b7280" fontSize={12} tickFormatter={(v) => `${v > 0 ? '+' : ''}${v}`} />
              <Tooltip
                contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, color: '#f3f4f6' }}
                formatter={(value: number) => [`${value > 0 ? '+' : ''}${value.toFixed(2)}%`, 'Variação NDVI']}
                labelFormatter={(label) => `Ano: ${label}`}
              />
              <ReferenceLine y={0} stroke="#6b7280" strokeDasharray="3 3" />
              <Bar dataKey="delta" radius={[4, 4, 0, 0]}>
                {variationData.map((entry, index) => (
                  <Cell key={index} fill={entry.delta >= 0 ? '#10B981' : '#ef4444'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Quick Actions */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        {[
          { label: 'Explorar Mapa', desc: 'Desenhe áreas, selecione bairros', path: '/map', color: '#10B981' },
          { label: 'Timeline Histórica', desc: `${eventStats?.total || 0} eventos documentados`, path: '/timeline', color: '#8b5cf6' },
          { label: 'Comparar Áreas', desc: 'Analise mudanças lado a lado', path: '/compare', color: '#06b6d4' },
        ].map(({ label, desc, path, color }) => (
          <motion.div
            key={path}
            className="glass glass-hover"
            style={{ padding: 20, cursor: 'pointer' }}
            whileHover={{ scale: 1.02 }}
            onClick={() => navigate(path)}
          >
            <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>{label}</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 12 }}>{desc}</p>
            <div style={{ display: 'flex', alignItems: 'center', color, fontSize: 13, fontWeight: 600 }}>
              Abrir <ArrowRight size={16} style={{ marginLeft: 4 }} />
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
