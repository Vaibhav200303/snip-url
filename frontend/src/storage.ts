import type { UrlRecord } from './types'

const RECENT_KEY = 'snipurl.recent'
const MAX_RECENT = 8

export function getRecent(): UrlRecord[] {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) ?? '[]') as UrlRecord[]
  } catch {
    return []
  }
}

export function addRecent(item: UrlRecord): UrlRecord[] {
  const recent = [item, ...getRecent().filter((entry) => entry.short_code !== item.short_code)].slice(0, MAX_RECENT)
  localStorage.setItem(RECENT_KEY, JSON.stringify(recent))
  return recent
}
