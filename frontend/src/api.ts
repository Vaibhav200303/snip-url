import type { Analytics, PublicAnalytics, UrlList, UrlRecord } from './types'

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  status: number
  code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, init)
  } catch {
    throw new ApiError(0, 'network_error', 'Cannot reach SnipURL. Check your connection and try again.')
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const code = payload?.error?.code ?? 'request_failed'
    const safeMessages: Record<string, string> = {
      alias_conflict: 'That custom alias is already in use.',
      validation_error: 'Please check the URL, alias, and expiration date.',
      rate_limited: 'Too many requests. Please wait a moment and try again.',
      unauthorized: 'The admin API key is invalid.',
      url_not_found: 'This short link no longer exists.',
      url_expired: 'This short link has expired.',
      url_disabled: 'This short link is disabled.',
      analytics_not_found: 'No active SnipURL was found for that address.',
    }
    throw new ApiError(response.status, code, safeMessages[code] ?? 'The request could not be completed.')
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

function adminHeaders(apiKey: string, json = false): HeadersInit {
  return { 'X-API-Key': apiKey, ...(json ? { 'Content-Type': 'application/json' } : {}) }
}

export function createUrl(body: { long_url: string; custom_alias?: string; expiration_at?: string }) {
  return request<UrlRecord>('/api/v1/urls', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function getPublicAnalytics(url: string) {
  return request<PublicAnalytics>('/api/v1/public/analytics', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
}

export function listUrls(apiKey: string, cursor?: string) {
  const query = cursor ? `?cursor=${encodeURIComponent(cursor)}` : ''
  return request<UrlList>(`/api/v1/urls${query}`, { headers: adminHeaders(apiKey) })
}

export function updateUrl(apiKey: string, code: string, body: { is_enabled: boolean }) {
  return request<UrlRecord>(`/api/v1/urls/${encodeURIComponent(code)}`, {
    method: 'PATCH', headers: adminHeaders(apiKey, true), body: JSON.stringify(body),
  })
}

export function deleteUrl(apiKey: string, code: string) {
  return request<void>(`/api/v1/urls/${encodeURIComponent(code)}`, {
    method: 'DELETE', headers: adminHeaders(apiKey),
  })
}

export function getAnalytics(apiKey: string, code: string, from: string, to: string) {
  return request<Analytics>(
    `/api/v1/urls/${encodeURIComponent(code)}/analytics?from=${from}&to=${to}`,
    { headers: adminHeaders(apiKey) },
  )
}
