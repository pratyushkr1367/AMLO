'use client'

import { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, AlertCircle, Info, X } from 'lucide-react'
import clsx from 'clsx'
import type { LiveAlert } from '@/lib/types'

const SEV_CONFIG = {
  CRITICAL:  { icon: AlertTriangle, color: 'text-status-critical', bg: 'bg-status-critical/10', border: 'border-status-critical/30' },
  DEGRADING: { icon: AlertCircle,   color: 'text-status-degrading', bg: 'bg-status-degrading/10', border: 'border-status-degrading/30' },
  NORMAL:    { icon: Info,          color: 'text-status-normal',    bg: 'bg-status-normal/10',    border: 'border-status-normal/30'    },
}

function AlertItem({ alert, onDismiss }: { alert: LiveAlert; onDismiss: () => void }) {
  const sev = alert.payload?.severity ?? 'NORMAL'
  const cfg = SEV_CONFIG[sev as keyof typeof SEV_CONFIG] ?? SEV_CONFIG.NORMAL
  const Icon = cfg.icon

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 40, height: 0 }}
      animate={{ opacity: 1, x: 0, height: 'auto' }}
      exit={{ opacity: 0, x: -40, height: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 28 }}
      className={clsx('relative flex items-start gap-3 p-3 rounded-lg border', cfg.bg, cfg.border)}
    >
      <Icon className={clsx('w-4 h-4 mt-0.5 shrink-0', cfg.color)} />
      <div className='flex-1 min-w-0'>
        <div className='flex items-center gap-2 mb-0.5'>
          <span className={clsx('text-xs font-mono font-bold', cfg.color)}>{sev}</span>
          <span className='text-xs font-mono text-slate-300'>{alert.entity_id}</span>
          <span className='text-xs text-slate-500'>{alert.payload?.sensor_type}</span>
        </div>
        <p className='text-xs text-slate-400 leading-relaxed'>
          avg {alert.payload?.average_value} — {alert.event_type}
        </p>
        <p className='text-[10px] text-slate-600 font-mono mt-1'>
          {new Date(alert.timestamp).toLocaleTimeString()}
        </p>
      </div>
      <button onClick={onDismiss} className='shrink-0 text-slate-600 hover:text-slate-300 transition-colors'>
        <X className='w-3 h-3' />
      </button>
    </motion.div>
  )
}

export function LiveAlertsFeed({ maxItems = 20 }: { maxItems?: number }) {
  const [alerts, setAlerts] = useState<LiveAlert[]>([])
  const wsRef = useRef<WebSocket | null>(null)

  // Pre-load historical alerts from MongoDB on mount
  useEffect(() => {
    fetch('/api/alerts/recent?limit=20')
      .then(r => r.ok ? r.json() : [])
      .then((data: object[]) => {
        if (!Array.isArray(data)) return
        const history: LiveAlert[] = data.map((d: object) => ({
          ...(d as Record<string, unknown>),
          id: crypto.randomUUID(),
        } as LiveAlert))
        setAlerts(history.slice(0, maxItems))
      })
      .catch(() => { /* service not running yet */ })
  }, [maxItems])

  // WebSocket for live incoming events
  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(`ws://${process.env.NEXT_PUBLIC_BACKEND_HOST || 'localhost'}:8006/ws/alerts`)
      wsRef.current = ws

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          const alert: LiveAlert = {
            ...data,
            id: crypto.randomUUID(),
            timestamp: data.timestamp ?? new Date().toISOString(),
          }
          setAlerts(prev => [alert, ...prev].slice(0, maxItems))
        } catch { /* ignore parse errors */ }
      }

      ws.onclose = () => setTimeout(connect, 2000)
    }

    connect()
    return () => { wsRef.current?.close() }
  }, [maxItems])

  const dismiss = (id: string) => setAlerts(prev => prev.filter(a => a.id !== id))

  return (
    <div className='space-y-2'>
      <AnimatePresence mode='popLayout'>
        {alerts.length === 0 ? (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className='text-sm text-slate-600 font-mono text-center py-8'
          >
            Awaiting events...
          </motion.p>
        ) : (
          alerts.map(a => <AlertItem key={a.id} alert={a} onDismiss={() => dismiss(a.id)} />)
        )}
      </AnimatePresence>
    </div>
  )
}
