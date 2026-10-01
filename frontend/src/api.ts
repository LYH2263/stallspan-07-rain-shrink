export async function api<T = any>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch('/api' + path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  })
  if (!res.ok) {
    const text = await res.text()
    let message = text || res.statusText
    try {
      const parsed = JSON.parse(text)
      if (parsed?.detail) message = parsed.detail
    } catch {
      // keep raw body text
    }
    throw new Error(message)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}
