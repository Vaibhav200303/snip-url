import { useState, type ReactNode } from 'react'

export function Logo() {
  return <a className="logo" href="/" aria-label="SnipURL home"><span>S</span> SnipURL</a>
}

export function Icon({ name }: { name: 'copy' | 'open' | 'chart' | 'trash' | 'power' }) {
  const paths: Record<string, ReactNode> = {
    copy: <><rect x="8" y="8" width="11" height="11" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/></>,
    open: <><path d="M14 4h6v6M20 4l-9 9"/><path d="M18 13v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h5"/></>,
    chart: <><path d="M4 19V9M10 19V5M16 19v-7M22 19V3"/></>,
    trash: <><path d="M4 7h16M9 7V4h6v3M7 7l1 13h8l1-13"/></>,
    power: <><path d="M12 3v9"/><path d="M6.4 6.4a8 8 0 1 0 11.2 0"/></>,
  }
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>
}

export function CopyButton({ value, label = 'Copy' }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false)
  async function copy() {
    await navigator.clipboard.writeText(value)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1800)
  }
  return <button className="button ghost small" onClick={copy}><Icon name="copy" />{copied ? 'Copied!' : label}</button>
}

export function Header({ admin = false }: { admin?: boolean }) {
  return <header><Logo/><nav>{admin ? <a href="/">Create link</a> : <a href="/admin">Admin</a>}<a href="/docs" target="_blank">API docs</a></nav></header>
}

export function Spinner() {
  return <span className="spinner" aria-label="Loading" />
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>
}
