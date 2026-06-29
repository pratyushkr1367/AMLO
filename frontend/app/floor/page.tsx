'use client'

import { motion } from 'framer-motion'
import useSWR from 'swr'
import { FloorGrid } from '@/components/FloorGrid'
import { StatusBadge } from '@/components/StatusBadge'
import { fetcher, API } from '@/lib/api'
import type { Machine, AGV } from '@/lib/types'

export default function FloorPage() {
  const { data: _machines } = useSWR(API.machines, fetcher, { refreshInterval: 3000 })
  const { data: _agvs }     = useSWR(API.agvs,     fetcher, { refreshInterval: 1500 })
  const machines: Machine[] = Array.isArray(_machines) ? _machines : []
  const agvs: AGV[]         = Array.isArray(_agvs)     ? _agvs     : []

  return (
    <div className='p-6 space-y-6'>
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className='text-xl font-bold text-slate-100'>Factory Floor</h1>
        <p className='text-xs text-slate-500 font-mono mt-0.5'>50×50 grid — live machine and AGV positions</p>
      </motion.div>

      <div className='grid grid-cols-1 xl:grid-cols-[1fr_280px] gap-6'>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }}>
          <FloorGrid />
        </motion.div>

        {/* Side panel */}
        <div className='space-y-4'>
          {/* AGV Status */}
          <motion.div initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }} className='card p-4'>
            <h3 className='text-xs font-mono text-slate-500 uppercase tracking-widest mb-3'>AGVs</h3>
            <div className='space-y-2'>
              {agvs.length === 0 && <p className='text-xs text-slate-600 font-mono'>No AGVs online</p>}
              {agvs.map(agv => (
                <motion.div key={agv.id} layout className='flex items-center justify-between py-2 border-b border-border last:border-0'>
                  <div>
                    <p className='text-sm font-mono font-semibold text-accent'>{agv.id}</p>
                    <p className='text-xs text-slate-500 font-mono'>
                      ({agv.position?.row ?? '—'}, {agv.position?.col ?? '—'})
                    </p>
                  </div>
                  <span className={`text-xs font-mono px-2 py-0.5 rounded-full ring-1 ${agv.busy ? 'text-status-degrading bg-status-degrading/10 ring-status-degrading/20' : 'text-status-normal bg-status-normal/10 ring-status-normal/20'}`}>
                    {agv.busy ? 'BUSY' : 'IDLE'}
                  </span>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Machine Status List */}
          <motion.div initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.25 }} className='card p-4'>
            <h3 className='text-xs font-mono text-slate-500 uppercase tracking-widest mb-3'>Machines</h3>
            <div className='space-y-2'>
              {machines.map(m => (
                <div key={m.id} className='flex items-center justify-between py-1.5 border-b border-border last:border-0'>
                  <p className='text-xs font-mono text-slate-300'>{m.machine_id}</p>
                  <StatusBadge status={m.status} size='xs' />
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}
