'use client'

import { motion } from 'framer-motion'
import { Bell } from 'lucide-react'
import { LiveAlertsFeed } from '@/components/LiveAlertsFeed'

export default function AlertsPage() {
  return (
    <div className='p-6 space-y-6'>
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} className='flex items-center gap-3'>
        <div className='flex items-center justify-center w-9 h-9 rounded-xl bg-status-critical/10 ring-1 ring-status-critical/20'>
          <Bell className='w-4 h-4 text-status-critical' />
        </div>
        <div>
          <h1 className='text-xl font-bold text-slate-100'>Live Alerts</h1>
          <p className='text-xs text-slate-500 font-mono mt-0.5'>WebSocket feed from Notification Service</p>
        </div>
        <div className='ml-auto flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-2 ring-1 ring-border'>
          <span className='relative flex h-2 w-2'>
            <span className='animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75' />
            <span className='relative inline-flex h-2 w-2 rounded-full bg-accent' />
          </span>
          <span className='text-xs font-mono text-accent'>LIVE</span>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className='card p-5'
      >
        <LiveAlertsFeed maxItems={50} />
      </motion.div>
    </div>
  )
}
