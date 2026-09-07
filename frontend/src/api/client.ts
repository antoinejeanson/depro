const BASE = '/api'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/**
 * Minimal fetch wrapper for the depro API.
 * Same-origin: the session cookie is attached automatically.
 */
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'same-origin',
    ...init,
    headers: { 'Content-Type': 'application/json', ...init.headers },
  })
  if (!res.ok) {
    throw new ApiError(res.status, `API error ${res.status} on ${path}`)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}
