'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import useSWR from 'swr'
import { ClipboardList, ChevronDown, ChevronUp } from 'lucide-react'
import clsx from 'clsx'
import { fetcher, API } from '@/lib/api'
import { StatusBadge } from '@/components/StatusBadge'
import type { WorkOrder, WorkOrderStatus, MachineStatus } from '@/lib/types'

const FILTERS: { label: string; value: string }[] = [
  { label: 'All',         value: 'ALL'        },
  { label: 'Open',        value: 'OPEN'       },
  { label: 'In Progress', value: 'IN_PROGRESS'},
  { label: 'Completed',   value: 'COMPLETED'  },
]

const PRIORITY_COLOR: Record<string, string> = {
  CRITICAL: 'text-status-critical bg-status-critical/10 ring-status-critical/20',
  HIGH:     'text-status-degrading bg-status-degrading/10 ring-status-degrading/20',
  MEDIUM:   'text-accent bg-accent/10 ring-accent/20',
  LOW:      'text-slate-400 bg-slate-400/10 ring-slate-400/20',
}

function woStatusToMachineStatus(s: WorkOrderStatus): MachineStatus {
  if (s === 'OPEN')        return 'CRITICAL'
  if (s === 'IN_PROGRESS') return 'DEGRADING'
  if (s === 'COMPLETED')   return 'NORMAL'
  return 'OFFLINE'
}

function WorkOrderRow({ wo, index }: { wo: WorkOrder; index: number }) {
  const [open, setOpen] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      className='card overflow-hidden'
    >
      <button
        onClick={() => setOpen(p => !p)}
        className='w-full flex items-center gap-4 p-4 text-left hover:bg-surface-3 transition-colors'
      >
        <span className='font-mono text-xs text-slate-500 w-8'>#{wo.id}</span>
        <div className='flex-1 min-w-0'>
          <p className='text-sm font-medium text-slate-200 truncate'>{wo.fault_type ?? 'Unknown Fault'}</p>
          <p className='text-xs text-slate-500 mt-0.5 truncate'>{wo.description?.slice(0, 80) ?? '—'}</p>
        </div>
        <span className={clsx('text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ring-1 shrink-0', PRIORITY_COLOR[wo.priority])}>
          {wo.priority}
        </span>
        <StatusBadge status={woStatusToMachineStatus(wo.status)} size='xs' />
        <span className='text-xs text-slate-600 font-mono shrink-0 hidden sm:block'>
          {new Date(wo.created_at).toLocaleDateString()}
        </span>
        {open ? <ChevronUp className='w-4 h-4 text-slate-500 shrink-0' /> : <ChevronDown className='w-4 h-4 text-slate-500 shrink-0' />}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className='overflow-hidden'
          >
            <div className='px-4 pb-4 pt-2 border-t border-border grid grid-cols-2 sm:grid-cols-4 gap-4'>
              <div>
                <p className='text-[10px] font-mono text-slate-600 uppercase mb-1'>Machine ID</p>
                <p className='text-sm font-mono text-slate-300'>{wo.machine_id}</p>
              </div>
              <div>
                <p className='text-[10px] font-mono text-slate-600 uppercase mb-1'>Technician</p>
                <p className='text-sm font-mono text-slate-300'>{wo.technician_id ?? '—'}</p>
              </div>
              <div>
                <p className='text-[10px] font-mono text-slate-600 uppercase mb-1'>Created</p>
                <p className='text-sm font-mono text-slate-300'>{new Date(wo.created_at).toLocaleString()}</p>
              </div>
              <div>
                <p className='text-[10px] font-mono text-slate-600 uppercase mb-1'>Completed</p>
                <p className='text-sm font-mono text-slate-300'>{wo.completed_at ? new Date(wo.completed_at).toLocaleString() : '—'}</p>
              </div>
              {wo.description && (
                <div className='col-span-full'>
                  <p className='text-[10px] font-mono text-slate-600 uppercase mb-1'>Description</p>
                  <p className='text-sm text-slate-400 leading-relaxed'>{wo.description}</p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default function WorkOrdersPage() {
  const [filter, setFilter] = useState('ALL')
  const { data: _workOrders } = useSWR(API.workOrders, fetcher, { refreshInterval: 5000 })
  const workOrders: WorkOrder[] = Array.isArray(_workOrders) ? _workOrders : []

  const filtered = filter === 'ALL' ? workOrders : workOrders.filter(w => w.status === filter)

  return (
    <div className='p-6 space-y-6'>
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} className='flex items-center gap-3'>
        <div className='flex items-center justify-center w-9 h-9 rounded-xl bg-accent/10 ring-1 ring-accent/20'>
          <ClipboardList className='w-4 h-4 text-accent' />
        </div>
        <div>
          <h1 className='text-xl font-bold text-slate-100'>Work Orders</h1>
          <p className='text-xs text-slate-500 font-mono mt-0.5'>{workOrders.length} total</p>
        </div>
      </motion.div>

      {/* Filters */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }} className='flex gap-2'>
        {FILTERS.map(f => (
          <motion.button
            key={f.value}
            onClick={() => setFilter(f.value)}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.97 }}
            className={clsx(
              'px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-colors',
              filter === f.value
                ? 'bg-accent/10 text-accent ring-1 ring-accent/30'
                : 'text-slate-400 hover:text-slate-200 bg-surface-2 ring-1 ring-border',
            )}
          >
            {f.label}
          </motion.button>
        ))}
      </motion.div>

      {/* List */}
      <div className='space-y-2'>
        <AnimatePresence>
          {filtered.length === 0 && (
            <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className='text-center text-slate-600 font-mono text-sm py-12'>
              No work orders
            </motion.p>
          )}
          {filtered.map((wo, i) => <WorkOrderRow key={wo.id} wo={wo} index={i} />)}
        </AnimatePresence>
      </div>
    </div>
  )
}
