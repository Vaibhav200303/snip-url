export interface UrlRecord {
  short_code: string
  short_url: string
  long_url: string
  created_at: string
  expiration_at: string | null
  is_custom: boolean
  is_enabled: boolean
}

export interface UrlList {
  items: UrlRecord[]
  next_cursor: string | null
}

export interface DailyClicks {
  date: string
  clicks: number
}

export interface Analytics {
  short_code: string
  total_clicks: number
  daily: DailyClicks[]
}
