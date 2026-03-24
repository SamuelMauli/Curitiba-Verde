import { motion } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'

interface Props {
  title: string
  value: string
  subtitle?: string
  icon: LucideIcon
  trend?: number
  color?: string
}

export default function StatCard({ title, value, subtitle, icon: Icon, trend, color = '#10B981' }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass glass-hover"
      style={{ padding: 20, minWidth: 200 }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 6 }}>{title}</p>
          <p style={{ fontSize: 28, fontWeight: 700, color }}>{value}</p>
          {subtitle && <p style={{ color: 'var(--text-secondary)', fontSize: 12, marginTop: 4 }}>{subtitle}</p>}
        </div>
        <div style={{
          width: 42, height: 42,
          background: `${color}15`,
          borderRadius: 10,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon size={20} color={color} />
        </div>
      </div>
      {trend !== undefined && (
        <div style={{
          marginTop: 10,
          fontSize: 13,
          color: trend >= 0 ? '#10B981' : '#ef4444',
          fontWeight: 600,
        }}>
          {trend >= 0 ? '\u2191' : '\u2193'} {Math.abs(trend).toFixed(1)}% vs 2000
        </div>
      )}
    </motion.div>
  )
}
