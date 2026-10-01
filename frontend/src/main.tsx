import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import Admin from './Admin'
import Home from './Home'
import './styles.css'

const Page = window.location.pathname === '/admin' ? Admin : Home

createRoot(document.getElementById('root')!).render(<StrictMode><Page /></StrictMode>)
