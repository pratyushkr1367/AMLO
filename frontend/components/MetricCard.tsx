'use client'

import { motion } from 'framer-motion'
import clsx from 'clsx'
import type { LucideIcon } from 'lucide-react'

interface Props {
  label: string
  value: string | number
  subtext?: string
  icon: LucideIcon
  color?: 'cyan' | 'red' | 'amber' | 'green'
  index?: number
}

const colors = {
  cyan:  { icon: 'text-accent',          bg: 'bg-accent/10',          ring: 'ring-accent/20'          },
  red:   { icon: 'text-status-critical', bg: 'bg-status-critical/10', ring: 'ring-status-critical/20' },
  amber: { icon: 'text-status-degrading',bg: 'bg-status-degrading/10',ring: 'ring-status-degrading/20'},
  green: { icon: 'text-status-normal',   bg: 'bg-status-normal/10',   ring: 'ring-status-normal/20'   },
}

export function MetricCard({ label, value, subtext, icon: Icon, color = 'cyan', index = 0 }: Props) {
  const c = colors[color]
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.35 }}
      whileHover={{ scale: 1.025, transition: { duration: 0.15 } }}
      className='card card-hover p-5 cursor-default'
    >
      <div className='flex items-start justify-between'>
        <div>
          <p className='text-xs font-mono text-slate-500 uppercase tracking-widest mb-2'>{label}</p>
          <motion.p
            key={String(value)}
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            className='text-3xl font-bold text-slate-100'
          >
            {value}
          </motion.p>
          {subtext && <p className='text-xs text-slate-500 mt-1'>{subtext}</p>}
        </div>
        <div className={clsx('flex items-center justify-center w-10 h-10 rounded-xl ring-1', c.bg, c.ring)}>
          <Icon className={clsx('w-5 h-5', c.icon)} />
        </div>
      </div>
    </motion.div>
  )
}
