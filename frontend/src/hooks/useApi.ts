const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export function getImageUrl(path: string): string {
  return `${API_BASE}${path}`
}
