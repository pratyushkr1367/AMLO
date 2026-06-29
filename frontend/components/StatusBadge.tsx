'use client'

import { motion } from 'framer-motion'
import clsx from 'clsx'
import type { MachineStatus } from '@/lib/types'

const config: Record<MachineStatus, { label: string; dot: string; text: string; ring: string; animate: boolean }> = {
  NORMAL:    { label: 'NORMAL',    dot: 'bg-status-normal',    text: 'text-status-normal',    ring: 'ring-status-normal/20',    animate: false },
  DEGRADING: { label: 'DEGRADING', dot: 'bg-status-degrading', text: 'text-status-degrading', ring: 'ring-status-degrading/20', animate: true  },
  CRITICAL:  { label: 'CRITICAL',  dot: 'bg-status-critical',  text: 'text-status-critical',  ring: 'ring-status-critical/20',  animate: true  },
  OFFLINE:   { label: 'OFFLINE',   dot: 'bg-status-offline',   text: 'text-status-offline',   ring: 'ring-status-offline/20',   animate: false },
}

export function StatusBadge({ status, size = 'sm' }: { status: MachineStatus; size?: 'xs' | 'sm' | 'md' }) {
  const c = config[status]
  return (
    <span className={clsx(
      'inline-flex items-center gap-1.5 rounded-full font-mono font-medium ring-1',
      c.text, c.ring,
      size === 'xs' && 'px-2 py-0.5 text-[10px]',
      size === 'sm' && 'px-2.5 py-1 text-xs',
      size === 'md' && 'px-3 py-1.5 text-sm',
    )}>
      <span className='relative flex h-1.5 w-1.5'>
        {c.animate && (
          <motion.span
            className={clsx('absolute inline-flex h-full w-full rounded-full opacity-75', c.dot)}
            animate={{ scale: [1, 2.2, 1], opacity: [0.75, 0, 0.75] }}
            transition={{ duration: 1.4, repeat: Infinity }}
          />
        )}
        <span className={clsx('relative inline-flex h-1.5 w-1.5 rounded-full', c.dot)} />
      </span>
      {c.label}
    </span>
  )
}
