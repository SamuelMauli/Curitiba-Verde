interface Props {
  years: number[]
  value: number
  onChange: (year: number) => void
}

export default function YearSlider({ years, value, onChange }: Props) {
  if (years.length === 0) return null

  const min = Math.min(...years)
  const max = Math.max(...years)

  return (
    <div style={{ padding: '8px 16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Ano</span>
        <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--accent)' }}>{value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={1}
        value={value}
        onChange={e => {
          const v = Number(e.target.value)
          const closest = years.reduce((a, b) => Math.abs(b - v) < Math.abs(a - v) ? b : a)
          onChange(closest)
        }}
        style={{
          width: '100%',
          accentColor: 'var(--accent)',
          cursor: 'pointer',
        }}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  )
}
