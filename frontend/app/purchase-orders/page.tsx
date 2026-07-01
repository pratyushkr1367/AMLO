'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import useSWR from 'swr'
import { ShoppingCart, CheckCircle, Clock, Loader2, Zap, Hand } from 'lucide-react'
import clsx from 'clsx'
import { fetcher, API } from '@/lib/api'
import type { PurchaseOrder, POStatus } from '@/lib/types'

const TABS: { label: string; value: POStatus }[] = [
  { label: 'Open',       value: 'OPEN'       },
  { label: 'Processing', value: 'PROCESSING' },
  { label: 'Completed',  value: 'COMPLETED'  },
]

const STATUS_CFG = {
  OPEN:       { color: 'text-accent',          bg: 'bg-accent/10',          border: 'border-accent/20',          icon: ShoppingCart },
  PROCESSING: { color: 'text-status-degrading', bg: 'bg-status-degrading/10', border: 'border-status-degrading/20', icon: Loader2      },
  COMPLETED:  { color: 'text-status-normal',    bg: 'bg-status-normal/10',    border: 'border-status-normal/20',    icon: CheckCircle  },
}

function PORow({ po, onApprove, approving }: {
  po: PurchaseOrder
  onApprove: (id: number) => void
  approving: boolean
}) {
  const cfg = STATUS_CFG[po.status]
  const Icon = cfg.icon
  const stockPct = Math.min(100, (po.quantity_at_order / Math.max(po.max_stock, 1)) * 100)

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0 }}
      whileHover={{ backgroundColor: 'rgba(17,24,39,0.6)' }}
      className='grid grid-cols-[1fr_2fr_80px_120px_120px_100px] gap-4 px-5 py-4 items-center transition-colors'
    >
      <span className='font-mono text-xs text-accent'>{po.part_number}</span>
      <span className='text-sm text-slate-300'>{po.part_name}</span>
      <span className='font-mono text-sm text-slate-200 font-semibold'>{po.quantity_ordered}</span>

      {/* Stock at order time bar */}
      <div className='space-y-1'>
        <div className='h-1.5 rounded-full bg-surface-4 overflow-hidden'>
          <div
            className={clsx('h-full rounded-full transition-all',
              po.quantity_at_order === 0 ? 'bg-status-critical' :
              po.quantity_at_order <= po.reorder_threshold ? 'bg-status-degrading' : 'bg-status-normal'
            )}
            style={{ width: `${stockPct}%` }}
          />
        </div>
        <p className='text-[10px] font-mono text-slate-600'>
          {po.quantity_at_order} / {po.max_stock} at order
        </p>
      </div>

      <div>
        <p className='text-[10px] font-mono text-slate-500'>
          {new Date(po.created_at).toLocaleString()}
        </p>
        {po.completed_at && (
          <p className='text-[10px] font-mono text-status-normal mt-0.5'>
            Done {new Date(po.completed_at).toLocaleTimeString()}
          </p>
        )}
      </div>

      <div className='flex items-center justify-end gap-2'>
        <span className={clsx('flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-mono border', cfg.bg, cfg.border, cfg.color)}>
          <Icon className={clsx('w-3 h-3', po.status === 'PROCESSING' && 'animate-spin')} />
          {po.status}
        </span>
        {po.status === 'OPEN' && (
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => onApprove(po.id)}
            disabled={approving}
            className='px-3 py-1 rounded-md bg-accent/20 hover:bg-accent/30 border border-accent/30 text-accent text-xs font-mono font-semibold transition-colors disabled:opacity-50'
          >
            Approve
          </motion.button>
        )}
      </div>
    </motion.div>
  )
}

export default function PurchaseOrdersPage() {
  const [activeTab, setActiveTab]     = useState<POStatus>('OPEN')
  const [approvingIds, setApprovingIds] = useState<Set<number>>(new Set())
  const [toggling, setToggling]       = useState(false)

  const { data: _all, mutate }        = useSWR(API.purchaseOrders, fetcher, { refreshInterval: 3000 })
  const { data: modeData, mutate: mutateMode } = useSWR(
    `${API.purchaseOrders}/approval-mode`, fetcher, { refreshInterval: 5000 }
  )
  const isAuto = modeData?.mode === 'auto'

  const toggleMode = async () => {
    setToggling(true)
    try {
      await fetch(`${API.purchaseOrders}/approval-mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: isAuto ? 'manual' : 'auto' }),
      })
      await mutateMode()
    } finally {
      setToggling(false)
    }
  }
  const all: PurchaseOrder[] = Array.isArray(_all) ? _all : []

  const counts = {
    OPEN:       all.filter(p => p.status === 'OPEN').length,
    PROCESSING: all.filter(p => p.status === 'PROCESSING').length,
    COMPLETED:  all.filter(p => p.status === 'COMPLETED').length,
  }

  const visible = all.filter(p => p.status === activeTab)

  const approve = async (id: number) => {
    setApprovingIds(prev => new Set(prev).add(id))
    try {
      await fetch(`${API.purchaseOrders}/${id}/approve`, { method: 'PATCH' })
      await mutate()
    } finally {
      setApprovingIds(prev => { const s = new Set(prev); s.delete(id); return s })
    }
  }

  return (
    <div className='p-6 space-y-6'>
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} className='flex items-center gap-3'>
        <div className='flex items-center justify-center w-9 h-9 rounded-xl bg-accent/10 ring-1 ring-accent/20'>
          <ShoppingCart className='w-4 h-4 text-accent' />
        </div>
        <div className='flex-1'>
          <h1 className='text-xl font-bold text-slate-100'>Purchase Orders</h1>
          <p className='text-xs text-slate-500 font-mono mt-0.5'>
            Auto-created when inventory falls below reorder threshold
          </p>
        </div>
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={toggleMode}
          disabled={toggling || !modeData}
          title={isAuto ? 'Switch to manual approval' : 'Switch to automatic approval'}
          className={clsx(
            'flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono font-semibold transition-colors disabled:opacity-50',
            isAuto
              ? 'bg-status-normal/10 border-status-normal/20 text-status-normal hover:bg-status-normal/20'
              : 'bg-surface-2 border-border text-slate-400 hover:text-slate-200 hover:border-border-bright',
          )}
        >
          {toggling
            ? <Loader2 className='w-3 h-3 animate-spin' />
            : isAuto ? <Zap className='w-3 h-3' /> : <Hand className='w-3 h-3' />
          }
          {isAuto ? 'Auto-Approve' : 'Manual Approve'}
        </motion.button>
      </motion.div>

      {/* Tabs */}
      <div className='flex gap-1 p-1 rounded-lg bg-surface-2 w-fit'>
        {TABS.map(tab => (
          <button
            key={tab.value}
            onClick={() => setActiveTab(tab.value)}
            className={clsx(
              'relative px-4 py-1.5 rounded-md text-xs font-mono font-semibold transition-colors',
              activeTab === tab.value ? 'text-slate-100' : 'text-slate-500 hover:text-slate-300'
            )}
          >
            {activeTab === tab.value && (
              <motion.div layoutId='po-tab' className='absolute inset-0 rounded-md bg-surface-4' />
            )}
            <span className='relative z-10'>
              {tab.label}
              {counts[tab.value] > 0 && (
                <span className={clsx(
                  'ml-1.5 px-1.5 py-0.5 rounded-full text-[10px]',
                  tab.value === 'OPEN' ? 'bg-accent/20 text-accent' :
                  tab.value === 'PROCESSING' ? 'bg-status-degrading/20 text-status-degrading' :
                  'bg-status-normal/20 text-status-normal'
                )}>
                  {counts[tab.value]}
                </span>
              )}
            </span>
          </button>
        ))}
      </div>

      {/* Table */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className='card overflow-hidden'>
        <div className='grid grid-cols-[1fr_2fr_80px_120px_120px_100px] gap-4 px-5 py-3 border-b border-border'>
          {['Part No.', 'Name', 'Qty', 'Stock Level', 'Created', 'Action'].map(h => (
            <span key={h} className='text-[10px] font-mono text-slate-600 uppercase tracking-widest'>{h}</span>
          ))}
        </div>
        <div className='divide-y divide-border'>
          <AnimatePresence mode='popLayout'>
            {visible.length === 0 ? (
              <motion.p
                key='empty'
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className='text-center text-slate-600 font-mono text-sm py-10'
              >
                {activeTab === 'OPEN' ? 'No open purchase orders — inventory levels are healthy' :
                 activeTab === 'PROCESSING' ? 'No orders being processed' :
                 'No completed orders yet'}
              </motion.p>
            ) : (
              visible.map(po => (
                <PORow
                  key={po.id}
                  po={po}
                  onApprove={approve}
                  approving={approvingIds.has(po.id)}
                />
              ))
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      {activeTab === 'PROCESSING' && counts.PROCESSING > 0 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className='flex items-center gap-2 text-xs font-mono text-status-degrading'>
          <Clock className='w-3.5 h-3.5' />
          Inventory will update automatically in ~10 seconds after approval
        </motion.div>
      )}
    </div>
  )
}
