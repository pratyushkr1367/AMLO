'use client'

import { motion } from 'framer-motion'
import useSWR from 'swr'
import { Package } from 'lucide-react'
import clsx from 'clsx'
import { fetcher, API } from '@/lib/api'
import type { InventoryItem } from '@/lib/types'

function StockBar({ qty, min }: { qty: number; min: number }) {
  const pct = Math.min(100, (qty / Math.max(min * 3, 1)) * 100)
  const color = qty === 0 ? 'bg-status-critical' : qty <= min ? 'bg-status-degrading' : 'bg-status-normal'
  return (
    <div className='flex items-center gap-2'>
      <div className='flex-1 h-1.5 rounded-full bg-surface-4 overflow-hidden'>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className={clsx('h-full rounded-full', color)}
        />
      </div>
      <span className={clsx(
        'text-xs font-mono w-6 text-right font-semibold',
        qty === 0 ? 'text-status-critical' : qty <= min ? 'text-status-degrading' : 'text-status-normal',
      )}>
        {qty}
      </span>
    </div>
  )
}

export default function InventoryPage() {
  const { data: _items } = useSWR(API.inventory, fetcher, { refreshInterval: 10000 })
  const items: InventoryItem[] = Array.isArray(_items) ? _items : []

  const outOfStock = items.filter(i => i.quantity === 0).length
  const lowStock   = items.filter(i => i.quantity > 0 && i.quantity <= i.reorder_threshold).length

  return (
    <div className='p-6 space-y-6'>
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} className='flex items-center gap-3'>
        <div className='flex items-center justify-center w-9 h-9 rounded-xl bg-accent/10 ring-1 ring-accent/20'>
          <Package className='w-4 h-4 text-accent' />
        </div>
        <div>
          <h1 className='text-xl font-bold text-slate-100'>Inventory</h1>
          <p className='text-xs text-slate-500 font-mono mt-0.5'>
            {items.length} parts · {outOfStock} out of stock · {lowStock} low
          </p>
        </div>
      </motion.div>

      {(outOfStock > 0 || lowStock > 0) && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className='flex gap-3'>
          {outOfStock > 0 && (
            <div className='flex items-center gap-2 px-3 py-1.5 rounded-lg bg-status-critical/10 ring-1 ring-status-critical/20'>
              <span className='w-2 h-2 rounded-full bg-status-critical' />
              <span className='text-xs font-mono text-status-critical'>{outOfStock} out of stock</span>
            </div>
          )}
          {lowStock > 0 && (
            <div className='flex items-center gap-2 px-3 py-1.5 rounded-lg bg-status-degrading/10 ring-1 ring-status-degrading/20'>
              <span className='w-2 h-2 rounded-full bg-status-degrading' />
              <span className='text-xs font-mono text-status-degrading'>{lowStock} low stock</span>
            </div>
          )}
        </motion.div>
      )}

      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className='card overflow-hidden'>
        <div className='grid grid-cols-[1fr_2fr_80px_1.5fr_80px] gap-4 px-5 py-3 border-b border-border'>
          {['Part No.', 'Name', 'Unit', 'Stock Level', 'Reorder At'].map(h => (
            <span key={h} className='text-[10px] font-mono text-slate-600 uppercase tracking-widest'>{h}</span>
          ))}
        </div>
        <div className='divide-y divide-border'>
          {items.length === 0 && (
            <p className='text-center text-slate-600 font-mono text-sm py-10'>No inventory data</p>
          )}
          {items.map((item, i) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.03 }}
              whileHover={{ backgroundColor: 'rgba(17,24,39,0.8)' }}
              className='grid grid-cols-[1fr_2fr_80px_1.5fr_80px] gap-4 px-5 py-3.5 items-center transition-colors'
            >
              <span className='font-mono text-xs text-accent'>{item.part_number}</span>
              <span className='text-sm text-slate-300'>{item.part_name}</span>
              <span className='text-xs font-mono text-slate-500'>{item.unit}</span>
              <StockBar qty={item.quantity} min={item.reorder_threshold} />
              <span className='text-xs font-mono text-slate-500'>{item.reorder_threshold}</span>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  )
}
