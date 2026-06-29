'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import useSWR from 'swr'
import { fetcher, API } from '@/lib/api'
import type { Machine, AGV } from '@/lib/types'

const CELL = 13
const GRID = 50
const SIZE = CELL * GRID

const STATUS_COLOR: Record<string, string> = {
  NORMAL:    '#4ade80',
  DEGRADING: '#fbbf24',
  CRITICAL:  '#f87171',
  OFFLINE:   '#64748b',
}

const MACHINE_IDS: Record<string, string> = {
  '5,10':  'CNC-01',
  '5,20':  'CNC-02',
  '15,10': 'LATHE-01',
  '15,25': 'LATHE-02',
  '25,15': 'PRESS-01',
  '35,10': 'WELD-01',
  '35,30': 'WELD-02',
}

export function FloorGrid() {
  const { data: _machines } = useSWR(API.machines, fetcher, { refreshInterval: 3000 })
  const { data: _agvs }     = useSWR(API.agvs,     fetcher, { refreshInterval: 1500 })
  const machines: Machine[] = Array.isArray(_machines) ? _machines : []
  const agvs: AGV[]         = Array.isArray(_agvs)     ? _agvs     : []
  const [tooltip, setTooltip]   = useState<{ machine: Machine; x: number; y: number } | null>(null)

  const machineMap = Object.fromEntries(machines.map(m => [m.machine_id, m]))

  return (
    <div className='relative overflow-auto rounded-xl border border-border bg-surface-1 p-4'>
      <div className='mb-3 flex items-center gap-4 text-xs font-mono text-slate-500'>
        {Object.entries(STATUS_COLOR).map(([s, c]) => (
          <span key={s} className='flex items-center gap-1.5'>
            <span className='w-2.5 h-2.5 rounded-sm' style={{ background: c }} />
            {s}
          </span>
        ))}
      </div>

      <svg
        width={SIZE}
        height={SIZE}
        className='block'
        style={{ background: '#070c17' }}
      >
        {/* Grid lines */}
        <defs>
          <pattern id='grid' width={CELL} height={CELL} patternUnits='userSpaceOnUse'>
            <path d={`M ${CELL} 0 L 0 0 0 ${CELL}`} fill='none' stroke='#1a2438' strokeWidth='0.5' />
          </pattern>
        </defs>
        <rect width={SIZE} height={SIZE} fill='url(#grid)' />

        {/* Machines */}
        {Object.entries(MACHINE_IDS).map(([key, machineId]) => {
          const [row, col] = key.split(',').map(Number)
          const machine = machineMap[machineId]
          const color = machine ? STATUS_COLOR[machine.status] : '#64748b'
          const x = col * CELL
          const y = row * CELL

          return (
            <g key={machineId}
              className='cursor-pointer'
              onMouseEnter={machine ? () => setTooltip({ machine, x: col * CELL, y: row * CELL }) : undefined}
              onMouseLeave={() => setTooltip(null)}
            >
              <rect
                x={x} y={y} width={CELL * 2} height={CELL * 2}
                rx={2}
                fill={color}
                fillOpacity={0.25}
                stroke={color}
                strokeWidth={1.5}
              />
              {machine?.status === 'CRITICAL' && (
                <rect
                  x={x} y={y} width={CELL * 2} height={CELL * 2}
                  rx={2}
                  fill='none'
                  stroke={color}
                  strokeWidth={2}
                  opacity={0.6}
                >
                  <animate attributeName='opacity' values='0.6;0;0.6' dur='1.2s' repeatCount='indefinite' />
                  <animate attributeName='strokeWidth' values='2;4;2' dur='1.2s' repeatCount='indefinite' />
                </rect>
              )}
              <text
                x={x + CELL} y={y + CELL + 4}
                fill={color}
                fontSize={7}
                textAnchor='middle'
                fontFamily='monospace'
                fontWeight='600'
              >
                {machineId.replace('-', '')}
              </text>
            </g>
          )
        })}

        {/* AGVs */}
        {agvs.filter(agv => agv.position).map(agv => (
          <motion.circle
            key={agv.id}
            cx={agv.position.col * CELL + CELL / 2}
            cy={agv.position.row * CELL + CELL / 2}
            r={5}
            fill='#38bdf8'
            fillOpacity={0.9}
            stroke='#0ea5e9'
            strokeWidth={1.5}
            animate={{
              cx: agv.position.col * CELL + CELL / 2,
              cy: agv.position.row * CELL + CELL / 2,
            }}
            transition={{ type: 'spring', stiffness: 80, damping: 15 }}
          />
        ))}

        {/* AGV labels */}
        {agvs.filter(agv => agv.position).map(agv => (
          <text
            key={agv.id + '-label'}
            x={agv.position.col * CELL + CELL / 2}
            y={agv.position.row * CELL + CELL / 2 - 8}
            fill='#38bdf8'
            fontSize={6}
            textAnchor='middle'
            fontFamily='monospace'
          >
            {agv.id}
          </text>
        ))}
      </svg>

      {/* Tooltip */}
      <AnimatePresence>
        {tooltip && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className='absolute z-20 bg-surface-3 border border-border-bright rounded-lg p-3 shadow-xl pointer-events-none'
            style={{ left: tooltip.x + 40, top: tooltip.y + 20 }}
          >
            <p className='font-mono font-bold text-sm text-slate-100'>{tooltip.machine.machine_id}</p>
            <p className='text-xs text-slate-400'>{tooltip.machine.name}</p>
            <p className='text-xs font-mono mt-1' style={{ color: STATUS_COLOR[tooltip.machine.status] }}>
              ● {tooltip.machine.status}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
