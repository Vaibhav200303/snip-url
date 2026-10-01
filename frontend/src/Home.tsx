import { useState, type FormEvent } from 'react'
import { ApiError, createUrl, getPublicAnalytics } from './api'
import { CopyButton, Header, Icon, Logo, Spinner } from './components'
import { addRecent, getRecent } from './storage'
import type { PublicAnalytics, UrlRecord } from './types'

function formatDate(value: string | null) {
  return value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : 'Never'
}

export default function Home() {
  const [longUrl, setLongUrl] = useState('')
  const [alias, setAlias] = useState('')
  const [expiration, setExpiration] = useState('')
  const [result, setResult] = useState<UrlRecord | null>(null)
  const [recent, setRecent] = useState<UrlRecord[]>(getRecent)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [analyticsQuery, setAnalyticsQuery] = useState('')
  const [analytics, setAnalytics] = useState<PublicAnalytics | null>(null)
  const [analyticsError, setAnalyticsError] = useState('')
  const [analyticsLoading, setAnalyticsLoading] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      const parsed = new URL(longUrl)
      if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error()
    } catch {
      setError('Enter a valid http or https URL.')
      return
    }
    if (alias && !/^[A-Za-z0-9_-]{3,32}$/.test(alias)) {
      setError("Custom aliases must be 3–32 characters using letters, numbers, '_' or '-'.")
      return
    }
    if (expiration && new Date(expiration) <= new Date()) {
      setError('Expiration must be in the future.')
      return
    }
    setLoading(true)
    try {
      const item = await createUrl({
        long_url: longUrl,
        ...(alias ? { custom_alias: alias } : {}),
        ...(expiration ? { expiration_at: new Date(expiration).toISOString() } : {}),
      })
      setResult(item)
      setRecent(addRecent(item))
      setAlias('')
      setExpiration('')
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  async function lookupAnalytics(event: FormEvent) {
    event.preventDefault()
    if (!analyticsQuery.trim()) {
      setAnalyticsError('Enter a short code, SnipURL, or destination URL.')
      return
    }
    setAnalyticsError('')
    setAnalyticsLoading(true)
    try {
      setAnalytics(await getPublicAnalytics(analyticsQuery.trim()))
    } catch (cause) {
      setAnalytics(null)
      setAnalyticsError(cause instanceof ApiError ? cause.message : 'Could not load activity. Please try again.')
    } finally {
      setAnalyticsLoading(false)
    }
  }

  const maxClicks = Math.max(...(analytics?.daily.map((day) => day.clicks) ?? [0]), 1)

  return <div className="site-shell">
    <Header />
    <main className="home-main">
      <section className="intro-grid">
        <div className="hero">
          <h1>SnipURL</h1>
          <p>Fast links. Simple analytics. Built to scale.</p>
        </div>

        <div className="shortener-card card">
          <form onSubmit={submit} noValidate>
            <label className="wide">Long URL<span>Where should your short link go?</span>
              <input type="url" required value={longUrl} onChange={(e) => setLongUrl(e.target.value)} placeholder="https://example.com/a-very-long-url" autoFocus />
            </label>
            <div className="form-grid">
              <label>Custom alias <span>Optional</span>
                <div className="input-prefix"><b>/</b><input value={alias} onChange={(e) => setAlias(e.target.value)} placeholder="your-alias" maxLength={32}/></div>
              </label>
              <label>Expiration <span>Optional</span>
                <input type="datetime-local" value={expiration} onChange={(e) => setExpiration(e.target.value)} />
              </label>
            </div>
            {error && <div className="alert" role="alert">{error}</div>}
            <button className="button primary submit" disabled={loading}>{loading ? <><Spinner/> Shortening…</> : 'Shorten URL'}</button>
          </form>
        </div>
      </section>

      {result && <section className="result-card card appear" aria-live="polite">
        <div className="success-mark">✓</div>
        <div className="result-main">
          <span className="section-label">Your short link is ready</span>
          <a className="short-link" href={result.short_url} target="_blank">{result.short_url}</a>
          <p className="truncate">Destination: {result.long_url}</p>
          <div className="meta"><span>{result.is_custom ? 'Custom alias' : 'Generated code'}</span><span>Expires: {formatDate(result.expiration_at)}</span></div>
        </div>
        <div className="actions"><CopyButton value={result.short_url}/><a className="button ghost small" href={result.short_url} target="_blank"><Icon name="open"/>Open</a></div>
      </section>}

      <section className="public-analytics">
        <div className="section-heading analytics-heading">
          <div><span className="section-label">Public activity</span><h2>Check link analytics</h2></div>
          <p>Active links only · Last 30 days</p>
        </div>
        <div className="analytics-lookup card">
          <form onSubmit={lookupAnalytics} noValidate>
            <label htmlFor="analytics-url">Short code or URL
              <span>Use a SnipURL or its destination</span>
            </label>
            <div className="lookup-row">
              <input id="analytics-url" value={analyticsQuery} onChange={(event) => setAnalyticsQuery(event.target.value)} placeholder="abc123 or https://example.com" />
              <button className="button primary" disabled={analyticsLoading}>{analyticsLoading ? <><Spinner/>Checking…</> : 'Check activity'}</button>
            </div>
            {analyticsError && <div className="alert" role="alert">{analyticsError}</div>}
          </form>

          {analytics && <div className="public-analytics-result appear" aria-live="polite">
            <div className="public-total"><strong>{analytics.total_clicks.toLocaleString()}</strong><span>redirects in the last 30 days</span></div>
            <div className="public-chart" aria-label={`Daily redirects. Total ${analytics.total_clicks}.`}>
              {analytics.daily.map((day) => <div className="public-bar-wrap" key={day.date} title={`${day.date}: ${day.clicks}`}>
                <div className="public-bar" style={{ height: `${Math.max((day.clicks / maxClicks) * 100, day.clicks ? 5 : 2)}%` }} />
              </div>)}
            </div>
            <p>{analytics.matched_links === 1 ? '1 active link matched' : `${analytics.matched_links} active links matched`}</p>
          </div>}
        </div>
      </section>

      {recent.length > 0 && <section className="recent-section">
        <div className="section-heading"><div><span className="section-label">Local history</span><h2>Recent links</h2></div><p>Stored only in this browser</p></div>
        <div className="recent-list">{recent.map((item) => <article className="recent-row" key={item.short_code}>
          <div className="link-icon">↗</div><div className="recent-copy"><a href={item.short_url} target="_blank">{item.short_url}</a><p>{item.long_url}</p><time>{formatDate(item.created_at)}</time></div>
          <div className="actions icon-actions"><CopyButton value={item.short_url} label=""/><a className="button ghost small" aria-label="Open link" href={item.short_url} target="_blank"><Icon name="open"/></a></div>
        </article>)}</div>
      </section>}
    </main>
    <footer><Logo/><span>© {new Date().getFullYear()} SnipURL</span></footer>
  </div>
}
