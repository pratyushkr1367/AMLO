'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import useSWR from 'swr'
import { BarChart2, AlertTriangle, Clock, TrendingUp, Activity } from 'lucide-react'
import clsx from 'clsx'
import { fetcher, API } from '@/lib/api'

type OEERow       = { machine_id: string; machine_type: string; oee: number; availability: number; performance: number; quality: number; downtime_minutes: number; incidents: number }
type DowntimeRow  = { machine_id: string; machine_type: string; total_incidents: number; resolved_incidents: number; ongoing_incidents: number; total_downtime_hours: number; recent_incidents: { fault_type: string; started_at: string; resolved_at: string | null; duration_minutes: number; status: string }[] }
type PredictRow   = { machine_id: string; machine_type: string; mtbf_hours: number | null; last_failure: string | null; next_failure_est: string | null; hours_since_failure: number; risk_level: string; confidence: string; total_failures: number; overdue: boolean }
type Summary      = { total_machines: number; total_incidents: number; open_incidents: number; resolved_incidents: number; avg_resolution_min: number | null; avg_oee_pct: number; high_risk_machines: number; high_risk_machine_ids: string[] }

const TABS = [
  { id: 'oee',        label: 'OEE',        icon: Activity },
  { id: 'downtime',   label: 'Downtime',   icon: Clock },
  { id: 'predictive', label: 'Predictive', icon: TrendingUp },
] as const

const RISK_COLOR: Record<string, string> = {
  HIGH:    'text-status-critical bg-status-critical/10 ring-status-critical/20',
  MEDIUM:  'text-status-degrading bg-status-degrading/10 ring-status-degrading/20',
  LOW:     'text-status-normal bg-status-normal/10 ring-status-normal/20',
  UNKNOWN: 'text-slate-400 bg-slate-400/10 ring-slate-400/20',
}

function OEEBar({ value, color }: { value: number; color: string }) {
  return (
    <div className='flex items-center gap-2'>
      <div className='flex-1 h-2 rounded-full bg-surface-4 overflow-hidden'>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.7, ease: 'easeOut' }}
          className={clsx('h-full rounded-full', color)}
        />
      </div>
      <span className='text-xs font-mono text-slate-400 w-10 text-right'>{value}%</span>
    </div>
  )
}

function SummaryCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className='card p-4 space-y-1'
    >
      <p className='text-[10px] font-mono text-slate-500 uppercase tracking-widest'>{label}</p>
      <p className={clsx('text-2xl font-bold font-mono', color)}>{value}</p>
      {sub && <p className='text-xs text-slate-500'>{sub}</p>}
    </motion.div>
  )
}

export default function AnalyticsPage() {
  const [tab, setTab] = useState<'oee' | 'downtime' | 'predictive'>('oee')

  const { data: summary }    = useSWR<Summary>(API.analytics.summary,    fetcher, { refreshInterval: 15000 })
  const { data: oeeData }    = useSWR<OEERow[]>(API.analytics.oee,       fetcher, { refreshInterval: 15000 })
  const { data: downtime }   = useSWR<DowntimeRow[]>(API.analytics.downtime,  fetcher, { refreshInterval: 15000 })
  const { data: predictive } = useSWR<PredictRow[]>(API.analytics.predictive, fetcher, { refreshInterval: 15000 })

  const oee  = Array.isArray(oeeData)    ? oeeData    : []
  const down = Array.isArray(downtime)   ? downtime   : []
  const pred = Array.isArray(predictive) ? predictive : []

  return (
    <div className='p-6 space-y-6'>
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} className='flex items-center gap-3'>
        <div className='flex items-center justify-center w-9 h-9 rounded-xl bg-accent/10 ring-1 ring-accent/20'>
          <BarChart2 className='w-4 h-4 text-accent' />
        </div>
        <div>
          <h1 className='text-xl font-bold text-slate-100'>Analytics</h1>
          <p className='text-xs text-slate-500 font-mono mt-0.5'>OEE · Downtime · Predictive Maintenance</p>
        </div>
      </motion.div>

      {/* Summary cards */}
      {summary && (
        <div className='grid grid-cols-2 lg:grid-cols-4 gap-4'>
          <SummaryCard label='Avg OEE'         value={`${summary.avg_oee_pct}%`}    color='text-accent'           sub='last 24 hours' />
          <SummaryCard label='Open Incidents'  value={summary.open_incidents}        color='text-status-critical'  sub={`${summary.total_incidents} total`} />
          <SummaryCard label='Avg Resolution'  value={summary.avg_resolution_min ? `${summary.avg_resolution_min}m` : '—'} color='text-status-degrading' sub='per work order' />
          <SummaryCard label='High Risk'       value={summary.high_risk_machines}    color={summary.high_risk_machines > 0 ? 'text-status-critical' : 'text-status-normal'} sub={summary.high_risk_machine_ids.join(', ') || 'none'} />
        </div>
      )}

      {/* Tabs */}
      <div className='flex gap-1 p-1 rounded-xl bg-surface-1 ring-1 ring-border w-fit'>
        {TABS.map(t => {
          const Icon   = t.icon
          const active = tab === t.id
          return (
            <motion.button
              key={t.id}
              onClick={() => setTab(t.id)}
              whileTap={{ scale: 0.97 }}
              className={clsx(
                'flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-mono font-medium transition-colors',
                active ? 'bg-accent/20 text-accent ring-1 ring-accent/30' : 'text-slate-400 hover:text-slate-200',
              )}
            >
              <Icon className='w-3 h-3' />
              {t.label}
            </motion.button>
          )
        })}
      </div>

      {/* Tab content */}
      <AnimatePresence mode='wait'>

        {/* ── OEE ── */}
        {tab === 'oee' && (
          <motion.div key='oee' initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className='card overflow-hidden'>
            <div className='grid grid-cols-[120px_1fr_80px_80px_80px_100px] gap-4 px-5 py-3 border-b border-border'>
              {['Machine', 'OEE', 'Avail.', 'Perf.', 'Quality', 'Downtime'].map(h => (
                <span key={h} className='text-[10px] font-mono text-slate-600 uppercase tracking-widest'>{h}</span>
              ))}
            </div>
            <div className='divide-y divide-border'>
              {oee.length === 0 && <p className='text-center text-slate-600 font-mono text-sm py-10'>No data yet</p>}
              {oee.map((row, i) => (
                <motion.div
                  key={row.machine_id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className='grid grid-cols-[120px_1fr_80px_80px_80px_100px] gap-4 px-5 py-3.5 items-center'
                >
                  <span className='font-mono text-xs text-accent'>{row.machine_id}</span>
                  <OEEBar value={row.oee} color={row.oee >= 85 ? 'bg-status-normal' : row.oee >= 60 ? 'bg-status-degrading' : 'bg-status-critical'} />
                  <span className='text-xs font-mono text-slate-400'>{row.availability}%</span>
                  <span className='text-xs font-mono text-slate-400'>{row.performance}%</span>
                  <span className='text-xs font-mono text-slate-400'>{row.quality}%</span>
                  <span className='text-xs font-mono text-slate-500'>{row.downtime_minutes}m</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {/* ── Downtime ── */}
        {tab === 'downtime' && (
          <motion.div key='downtime' initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className='space-y-3'>
            {down.length === 0 && <p className='text-center text-slate-600 font-mono text-sm py-10 card p-6'>No downtime data yet</p>}
            {down.map((row, i) => (
              <motion.div
                key={row.machine_id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className='card p-4 space-y-3'
              >
                <div className='flex items-center justify-between'>
                  <div>
                    <span className='font-mono text-sm text-accent'>{row.machine_id}</span>
                    <span className='ml-2 text-xs text-slate-500 font-mono'>{row.machine_type}</span>
                  </div>
                  <div className='flex items-center gap-4 text-xs font-mono text-slate-400'>
                    <span><span className='text-status-critical'>{row.ongoing_incidents}</span> ongoing</span>
                    <span><span className='text-slate-200'>{row.resolved_incidents}</span> resolved</span>
                    <span className='text-status-degrading font-semibold'>{row.total_downtime_hours}h total</span>
                  </div>
                </div>
                {row.recent_incidents.length > 0 && (
                  <div className='space-y-1'>
                    {row.recent_incidents.map((inc, j) => (
                      <div key={j} className='flex items-center gap-3 text-xs font-mono text-slate-500 pl-2 border-l border-border'>
                        <span className={inc.status === 'ONGOING' ? 'text-status-critical' : 'text-status-normal'}>{inc.status}</span>
                        <span className='flex-1 text-slate-400 truncate'>{inc.fault_type ?? 'Unknown'}</span>
                        <span>{inc.duration_minutes}m</span>
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>
            ))}
          </motion.div>
        )}

        {/* ── Predictive ── */}
        {tab === 'predictive' && (
          <motion.div key='predictive' initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className='card overflow-hidden'>
            <div className='grid grid-cols-[120px_80px_100px_120px_1fr_100px] gap-4 px-5 py-3 border-b border-border'>
              {['Machine', 'Risk', 'MTBF', 'Last Failure', 'Next Est.', 'Failures'].map(h => (
                <span key={h} className='text-[10px] font-mono text-slate-600 uppercase tracking-widest'>{h}</span>
              ))}
            </div>
            <div className='divide-y divide-border'>
              {pred.length === 0 && <p className='text-center text-slate-600 font-mono text-sm py-10'>No data yet</p>}
              {pred.map((row, i) => (
                <motion.div
                  key={row.machine_id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className='grid grid-cols-[120px_80px_100px_120px_1fr_100px] gap-4 px-5 py-3.5 items-center'
                >
                  <span className='font-mono text-xs text-accent'>{row.machine_id}</span>
                  <span className={clsx('text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ring-1 w-fit', RISK_COLOR[row.risk_level])}>
                    {row.risk_level}
                  </span>
                  <span className='text-xs font-mono text-slate-400'>{row.mtbf_hours != null ? `${row.mtbf_hours}h` : '—'}</span>
                  <span className='text-xs font-mono text-slate-500'>
                    {row.last_failure ? new Date(row.last_failure).toLocaleDateString() : '—'}
                  </span>
                  <span className='text-xs font-mono text-slate-500'>
                    {row.next_failure_est
                      ? <span className={row.overdue ? 'text-status-critical' : 'text-slate-400'}>{new Date(row.next_failure_est).toLocaleString()}{row.overdue ? ' ⚠ overdue' : ''}</span>
                      : <span className='text-slate-600'>{row.confidence}</span>}
                  </span>
                  <span className='text-xs font-mono text-slate-500'>{row.total_failures}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
