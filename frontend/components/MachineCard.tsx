'use client'

import { motion } from 'framer-motion'
import clsx from 'clsx'
import { StatusBadge } from './StatusBadge'
import type { Machine } from '@/lib/types'

const typeColors: Record<string, string> = {
  CNC:    'text-blue-400 bg-blue-400/10 ring-blue-400/20',
  Lathe:  'text-purple-400 bg-purple-400/10 ring-purple-400/20',
  Press:  'text-orange-400 bg-orange-400/10 ring-orange-400/20',
  Welder: 'text-yellow-400 bg-yellow-400/10 ring-yellow-400/20',
}

const statusGlow: Record<string, string> = {
  NORMAL:    '',
  DEGRADING: 'animate-glow-amber',
  CRITICAL:  'animate-glow-red',
  OFFLINE:   '',
}

export function MachineCard({ machine, index }: { machine: Machine; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
      whileHover={{ scale: 1.03, transition: { duration: 0.15 } }}
      whileTap={{ scale: 0.98 }}
      className={clsx(
        'card p-4 cursor-default select-none',
        statusGlow[machine.status],
      )}
    >
      <div className='flex items-start justify-between mb-3'>
        <div>
          <p className='font-mono font-semibold text-slate-100 text-sm'>{machine.machine_id}</p>
          <p className='text-xs text-slate-500 mt-0.5'>{machine.name}</p>
        </div>
        <span className={clsx('text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full ring-1', typeColors[machine.machine_type] ?? 'text-slate-400 bg-slate-400/10 ring-slate-400/20')}>
          {machine.machine_type}
        </span>
      </div>

      <StatusBadge status={machine.status} size='xs' />

      <div className='mt-3 pt-3 border-t border-border flex items-center justify-between'>
        <span className='text-xs text-slate-600 font-mono'>
          ({machine.location_row}, {machine.location_col})
        </span>
        {machine.last_maintenance && (
          <span className='text-[10px] text-slate-600'>
            {new Date(machine.last_maintenance).toLocaleDateString()}
          </span>
        )}
      </div>
    </motion.div>
  )
}
