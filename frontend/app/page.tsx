'use client'

import { motion } from 'framer-motion'
import useSWR from 'swr'
import { AlertTriangle, ClipboardList, Cpu, Activity } from 'lucide-react'
import { MetricCard } from '@/components/MetricCard'
import { MachineCard } from '@/components/MachineCard'
import { LiveAlertsFeed } from '@/components/LiveAlertsFeed'
import { StatusBadge } from '@/components/StatusBadge'
import { fetcher, API } from '@/lib/api'
import type { Machine, WorkOrder } from '@/lib/types'

function Clock() {
  const { data: time = '--:--:--' } = useSWR('clock', () => new Date().toLocaleTimeString(), { refreshInterval: 1000 })
  return <span className='font-mono text-sm text-slate-500'>{time}</span>
}

export default function Dashboard() {
  const { data: _machines }    = useSWR(API.machines,    fetcher, { refreshInterval: 5000 })
  const { data: _workOrders }  = useSWR(API.workOrders,  fetcher, { refreshInterval: 5000 })
  const machines: Machine[]    = Array.isArray(_machines)   ? _machines   : []
  const workOrders: WorkOrder[] = Array.isArray(_workOrders) ? _workOrders : []

  const critical  = machines.filter(m => m.status === 'CRITICAL').length
  const degrading = machines.filter(m => m.status === 'DEGRADING').length
  const online    = machines.filter(m => m.status !== 'OFFLINE').length
  const openWO    = workOrders.filter(w => w.status === 'OPEN' || w.status === 'IN_PROGRESS').length
  const recentWO  = workOrders.slice(0, 5)

  return (
    <div className='p-6 space-y-6 min-h-full'>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        className='flex items-center justify-between'
      >
        <div>
          <h1 className='text-xl font-bold text-slate-100 tracking-tight'>Control Center</h1>
          <p className='text-xs text-slate-500 font-mono mt-0.5'>Autonomous Maintenance & Logistics Orchestrator</p>
        </div>
        <div className='flex items-center gap-4'>
          <Clock />
          <div className='flex items-center gap-2 px-3 py-1.5 rounded-full bg-status-normal/10 ring-1 ring-status-normal/20'>
            <span className='relative flex h-2 w-2'>
              <span className='animate-ping absolute inline-flex h-full w-full rounded-full bg-status-normal opacity-75' />
              <span className='relative inline-flex h-2 w-2 rounded-full bg-status-normal' />
            </span>
            <span className='text-xs font-mono text-status-normal'>OPERATIONAL</span>
          </div>
        </div>
      </motion.div>

      {/* Metrics */}
      <div className='grid grid-cols-2 lg:grid-cols-4 gap-4'>
        <MetricCard label='Critical Alerts'  value={critical}   icon={AlertTriangle} color='red'   index={0} subtext={`${degrading} degrading`} />
        <MetricCard label='Open Work Orders' value={openWO}     icon={ClipboardList} color='amber' index={1} />
        <MetricCard label='Machines Online'  value={`${online}/${machines.length}`} icon={Cpu} color='cyan' index={2} />
        <MetricCard label='System Health'    value={critical > 0 ? 'ALERT' : 'GOOD'} icon={Activity} color={critical > 0 ? 'red' : 'green'} index={3} />
      </div>

      {/* Machine Grid */}
      <div>
        <h2 className='text-xs font-mono text-slate-500 uppercase tracking-widest mb-3'>Machine Status</h2>
        <div className='grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3'>
          {machines.map((m, i) => <MachineCard key={m.id} machine={m} index={i} />)}
          {machines.length === 0 && (
            <div className='col-span-full text-center py-8 text-slate-600 font-mono text-sm'>
              Waiting for Asset Service...
            </div>
          )}
        </div>
      </div>

      {/* Bottom row */}
      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        {/* Live Alerts */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className='card p-5'>
          <h2 className='text-xs font-mono text-slate-500 uppercase tracking-widest mb-4'>Live Alerts</h2>
          <div className='max-h-64 overflow-y-auto pr-1'>
            <LiveAlertsFeed maxItems={10} />
          </div>
        </motion.div>

        {/* Recent Work Orders */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }} className='card p-5'>
          <h2 className='text-xs font-mono text-slate-500 uppercase tracking-widest mb-4'>Recent Work Orders</h2>
          <div className='space-y-2'>
            {recentWO.length === 0 && (
              <p className='text-sm text-slate-600 font-mono text-center py-8'>No work orders yet</p>
            )}
            {recentWO.map((wo, i) => (
              <motion.div
                key={wo.id}
                initial={{ opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className='flex items-center gap-3 p-3 rounded-lg bg-surface-1 border border-border hover:border-border-bright transition-colors'
              >
                <div className='flex-1 min-w-0'>
                  <p className='text-xs font-mono text-slate-200 truncate'>#{wo.id} — {wo.fault_type ?? 'Unknown'}</p>
                  <p className='text-[10px] text-slate-500 mt-0.5'>{new Date(wo.created_at).toLocaleString()}</p>
                </div>
                <StatusBadge status={wo.status === 'OPEN' ? 'CRITICAL' : wo.status === 'IN_PROGRESS' ? 'DEGRADING' : 'NORMAL'} size='xs' />
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  )
}
