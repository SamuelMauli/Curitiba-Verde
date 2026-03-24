import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { TreePine, TrendingDown, MapPin, Calendar, ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'
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
          value={latest ? `${latest.green_percent.toFixed(1)}%` : '\u2014'}
          subtitle={latest ? `${latest.green_area_ha.toFixed(0)} hectares` : ''}
          icon={TreePine}
          trend={trend}
        />
        <StatCard
          title="NDVI M\u00e9dio"
          value={latest ? latest.ndvi_mean.toFixed(3) : '\u2014'}
          subtitle="\u00cdndice de vegeta\u00e7\u00e3o"
          icon={TrendingDown}
          color="#f59e0b"
        />
        <StatCard
          title="Eventos Hist\u00f3ricos"
          value={eventStats ? String(eventStats.total) : '\u2014'}
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

      {/* Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
        {/* NDVI Time Series */}
        <div className="glass" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Evolu\u00e7\u00e3o do NDVI</h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={stats}>
              <defs>
                <linearGradient id="ndviGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="year" stroke="#6b7280" fontSize={12} />
              <YAxis stroke="#6b7280" fontSize={12} domain={[0, 1]} />
              <Tooltip
                contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, color: '#f3f4f6' }}
              />
              <Area type="monotone" dataKey="ndvi_mean" stroke="#10B981" fill="url(#ndviGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Green Area Bar Chart */}
        <div className="glass" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>\u00c1rea Verde (hectares)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={stats}>
              <XAxis dataKey="year" stroke="#6b7280" fontSize={12} />
              <YAxis stroke="#6b7280" fontSize={12} />
              <Tooltip
                contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8, color: '#f3f4f6' }}
              />
              <Bar dataKey="green_area_ha" fill="#10B981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Quick Actions */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        {[
          { label: 'Explorar Mapa', desc: 'Desenhe \u00e1reas, selecione bairros', path: '/map', color: '#10B981' },
          { label: 'Timeline Hist\u00f3rica', desc: `${eventStats?.total || 0} eventos documentados`, path: '/timeline', color: '#8b5cf6' },
          { label: 'Comparar \u00c1reas', desc: 'Analise mudan\u00e7as lado a lado', path: '/compare', color: '#06b6d4' },
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
