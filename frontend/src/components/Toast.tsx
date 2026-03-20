import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'

interface Toast {
  id: string
  message: string
  type: 'success' | 'error'
  fading: boolean
}

// Singleton store so useToast() works across components
type Listener = (toasts: Toast[]) => void
let toasts: Toast[] = []
const listeners = new Set<Listener>()

function notify() {
  listeners.forEach(l => l([...toasts]))
}

export function showToast(message: string, type: 'success' | 'error' = 'success') {
  const id = Math.random().toString(36).slice(2)
  toasts = [...toasts, { id, message, type, fading: false }]
  notify()

  // Start fade-out after 3.6s, remove at 4s
  setTimeout(() => {
    toasts = toasts.map(t => t.id === id ? { ...t, fading: true } : t)
    notify()
  }, 3600)
  setTimeout(() => {
    toasts = toasts.filter(t => t.id !== id)
    notify()
  }, 4000)
}

export function useToast() {
  return { showToast }
}

export function ToastContainer() {
  const [items, setItems] = useState<Toast[]>([])

  useEffect(() => {
    listeners.add(setItems)
    return () => { listeners.delete(setItems) }
  }, [])

  if (items.length === 0) return null

  return createPortal(
    <div style={{
      position: 'fixed', top: 60, right: 24, zIndex: 9999,
      display: 'flex', flexDirection: 'column', gap: 8,
    }}>
      {items.map(toast => (
        <div
          key={toast.id}
          style={{
            background: 'var(--bg-elevated)',
            border: `1px solid ${toast.type === 'success' ? 'var(--accent-teal)' : 'var(--accent-coral)'}`,
            borderRadius: 10,
            padding: '12px 18px',
            color: 'var(--text-primary)',
            fontSize: 14,
            maxWidth: 320,
            boxShadow: toast.type === 'success'
              ? '0 4px 20px rgba(0,229,204,0.12)'
              : '0 4px 20px rgba(255,107,107,0.12)',
            opacity: toast.fading ? 0 : 1,
            transition: 'opacity 0.4s ease',
          }}
          className="font-mono"
        >
          {toast.message}
        </div>
      ))}
    </div>,
    document.body
  )
}
