import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { ApiError, deleteUrl, getAnalytics, listUrls, updateUrl } from './api'
import { CopyButton, EmptyState, Header, Icon, Spinner } from './components'
import type { Analytics, UrlRecord } from './types'

const KEY = 'snipurl.admin-key'
const isoDate = (date: Date) => date.toISOString().slice(0, 10)
const today = new Date()
const monthAgo = new Date(Date.now() - 29 * 86400000)

function KeyGate({ onLogin }: { onLogin: (key: string) => void }) {
  const [key, setKey] = useState('')
  function submit(event: FormEvent) {
    event.preventDefault()
    if (key.trim()) onLogin(key.trim())
  }
  return <div className="admin-shell"><Header admin/><main className="login-wrap"><section className="login-card card">
    <div className="lock">⌁</div><span className="section-label">Restricted area</span><h1>Admin dashboard</h1>
    <p>Enter your admin API key to manage links and view analytics. The key stays in this browser session only.</p>
    <form onSubmit={submit}><label>Admin API key<input type="password" value={key} onChange={(event) => setKey(event.target.value)} autoComplete="off" autoFocus placeholder="Enter your key"/></label><button className="button primary" disabled={!key.trim()}>Continue</button></form>
  </section></main></div>
}

function ClickChart({ analytics }: { analytics: Analytics }) {
  const max = Math.max(...analytics.daily.map((day) => day.clicks), 1)
  return <div className="chart" aria-label="Daily click chart">{analytics.daily.map((day) => <div className="bar-wrap" key={day.date} title={`${day.date}: ${day.clicks} clicks`}><span>{day.clicks || ''}</span><div className="bar" style={{ height: `${Math.max((day.clicks / max) * 100, 3)}%` }}/><small>{day.date.slice(5)}</small></div>)}</div>
}

export default function Admin() {
  const [apiKey, setApiKey] = useState(() => sessionStorage.getItem(KEY) ?? '')
  const [items, setItems] = useState<UrlRecord[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<UrlRecord | null>(null)
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [from, setFrom] = useState(isoDate(monthAgo))
  const [to, setTo] = useState(isoDate(today))

  const load = useCallback(async (key: string, next?: string) => {
    setLoading(true); setError('')
    try {
      const result = await listUrls(key, next)
      setItems((current) => next ? [...current, ...result.items] : result.items)
      setCursor(result.next_cursor)
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Could not load URLs.')
      if (cause instanceof ApiError && cause.status === 401) { sessionStorage.removeItem(KEY); setApiKey('') }
    } finally { setLoading(false) }
  }, [])

  useEffect(() => {
    if (apiKey) queueMicrotask(() => void load(apiKey))
  }, [apiKey, load])

  function login(key: string) { sessionStorage.setItem(KEY, key); setApiKey(key) }
  function logout() { sessionStorage.removeItem(KEY); setApiKey(''); setItems([]); setSelected(null) }

  async function toggle(item: UrlRecord) {
    try {
      const updated = await updateUrl(apiKey, item.short_code, { is_enabled: !item.is_enabled })
      setItems((current) => current.map((entry) => entry.short_code === item.short_code ? updated : entry))
      if (selected?.short_code === item.short_code) setSelected(updated)
    } catch (cause) { setError(cause instanceof ApiError ? cause.message : 'Could not update the URL.') }
  }

  async function remove(item: UrlRecord) {
    if (!window.confirm(`Delete ${item.short_url}? This cannot be undone.`)) return
    try {
      await deleteUrl(apiKey, item.short_code)
      setItems((current) => current.filter((entry) => entry.short_code !== item.short_code))
      if (selected?.short_code === item.short_code) setSelected(null)
    } catch (cause) { setError(cause instanceof ApiError ? cause.message : 'Could not delete the URL.') }
  }

  async function viewAnalytics(item: UrlRecord) {
    setSelected(item); setAnalytics(null); setError('')
    try { setAnalytics(await getAnalytics(apiKey, item.short_code, from, to)) }
    catch (cause) { setError(cause instanceof ApiError ? cause.message : 'Could not load analytics.') }
  }

  if (!apiKey) return <KeyGate onLogin={login}/>

  return <div className="admin-shell"><Header admin/><main className="admin-main">
    <div className="admin-title"><div><span className="section-label">Management</span><h1>Link dashboard</h1><p>Manage every shortened URL and inspect click activity.</p></div><button className="button ghost" onClick={logout}>Clear key & log out</button></div>
    {error && <div className="alert" role="alert">{error}</div>}
    <section className="admin-grid">
      <div className="card table-card"><div className="table-header"><h2>All links</h2><span>{items.length} loaded</span></div>
        {items.length === 0 && !loading ? <EmptyState>No links found yet.</EmptyState> : <div className="table-scroll"><table><thead><tr><th>Link</th><th>Status</th><th>Created</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{items.map((item) => <tr key={item.short_code} className={selected?.short_code === item.short_code ? 'selected' : ''}><td><a href={item.short_url} target="_blank">/{item.short_code}</a><small>{item.long_url}</small></td><td><span className={`status ${item.is_enabled ? 'on' : 'off'}`}>{item.is_enabled ? 'Active' : 'Disabled'}</span></td><td>{new Date(item.created_at).toLocaleDateString()}</td><td><div className="row-actions"><button title="Analytics" onClick={() => void viewAnalytics(item)}><Icon name="chart"/></button><button title={item.is_enabled ? 'Disable' : 'Enable'} onClick={() => void toggle(item)}><Icon name="power"/></button><button title="Delete" className="danger" onClick={() => void remove(item)}><Icon name="trash"/></button></div></td></tr>)}</tbody></table></div>}
        {loading && <div className="loading-row"><Spinner/> Loading…</div>}{cursor && !loading && <button className="button ghost load-more" onClick={() => void load(apiKey, cursor)}>Load more</button>}
      </div>

      <aside className="card detail-card">{selected ? <><div className="detail-head"><div><span className="section-label">Link details</span><h2>/{selected.short_code}</h2></div><CopyButton value={selected.short_url} label=""/></div><dl><div><dt>Destination</dt><dd>{selected.long_url}</dd></div><div><dt>Type</dt><dd>{selected.is_custom ? 'Custom alias' : 'Generated'}</dd></div><div><dt>Expires</dt><dd>{selected.expiration_at ? new Date(selected.expiration_at).toLocaleString() : 'Never'}</dd></div></dl><div className="range"><label>From<input type="date" value={from} onChange={(event) => setFrom(event.target.value)}/></label><label>To<input type="date" value={to} onChange={(event) => setTo(event.target.value)}/></label><button className="button primary small" onClick={() => void viewAnalytics(selected)}>Refresh</button></div>{analytics ? <div className="analytics"><div className="total"><strong>{analytics.total_clicks}</strong><span>Total clicks</span></div><ClickChart analytics={analytics}/></div> : <div className="loading-row"><Spinner/> Loading analytics…</div>}</> : <EmptyState>Select the chart icon beside a link to view details and analytics.</EmptyState>}</aside>
    </section>
  </main></div>
}
