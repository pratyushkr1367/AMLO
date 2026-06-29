'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion } from 'framer-motion'
import { LayoutDashboard, Factory, Bell, ClipboardList, Package, ChevronLeft, ChevronRight, Cpu } from 'lucide-react'
import clsx from 'clsx'

const nav = [
  { href: '/',            label: 'Dashboard',     icon: LayoutDashboard },
  { href: '/floor',       label: 'Factory Floor', icon: Factory },
  { href: '/alerts',      label: 'Live Alerts',   icon: Bell },
  { href: '/work-orders', label: 'Work Orders',   icon: ClipboardList },
  { href: '/inventory',   label: 'Inventory',     icon: Package },
]

export function Sidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <motion.aside
      animate={{ width: collapsed ? 64 : 220 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className='relative flex flex-col h-full bg-surface-1 border-r border-border overflow-hidden shrink-0'
    >
      {/* Logo */}
      <div className='flex items-center gap-3 px-4 py-5 border-b border-border'>
        <div className='flex items-center justify-center w-8 h-8 rounded-lg bg-accent/10 ring-1 ring-accent/30 shrink-0'>
          <Cpu className='w-4 h-4 text-accent' />
        </div>
        <motion.span
          animate={{ opacity: collapsed ? 0 : 1, width: collapsed ? 0 : 'auto' }}
          transition={{ duration: 0.15 }}
          className='overflow-hidden whitespace-nowrap font-bold text-sm tracking-widest text-accent glow-text-cyan'
        >
          AMLO
        </motion.span>
      </div>

      {/* Nav */}
      <nav className='flex-1 py-4 space-y-1 px-2'>
        {nav.map(({ href, label, icon: Icon }) => {
          const active = pathname === href
          return (
            <Link key={href} href={href}>
              <motion.div
                whileHover={{ x: 3 }}
                whileTap={{ scale: 0.97 }}
                className={clsx(
                  'flex items-center gap-3 px-2.5 py-2.5 rounded-lg text-sm font-medium transition-colors cursor-pointer',
                  active
                    ? 'bg-accent/10 text-accent ring-1 ring-accent/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-surface-3',
                )}
              >
                <Icon className={clsx('w-4 h-4 shrink-0', active && 'text-accent')} />
                <motion.span
                  animate={{ opacity: collapsed ? 0 : 1, width: collapsed ? 0 : 'auto' }}
                  transition={{ duration: 0.15 }}
                  className='overflow-hidden whitespace-nowrap'
                >
                  {label}
                </motion.span>
                {active && !collapsed && (
                  <motion.div layoutId='active-pill' className='ml-auto w-1 h-1 rounded-full bg-accent' />
                )}
              </motion.div>
            </Link>
          )
        })}
      </nav>

      {/* System tag */}
      {!collapsed && (
        <div className='px-4 py-3 border-t border-border'>
          <div className='flex items-center gap-2'>
            <span className='relative flex h-2 w-2'>
              <span className='animate-ping absolute inline-flex h-full w-full rounded-full bg-status-normal opacity-75' />
              <span className='relative inline-flex h-2 w-2 rounded-full bg-status-normal' />
            </span>
            <span className='text-xs text-slate-500 font-mono'>SYSTEM ONLINE</span>
          </div>
        </div>
      )}

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(p => !p)}
        className='absolute -right-3 top-6 z-10 flex items-center justify-center w-6 h-6 rounded-full bg-surface-3 border border-border text-slate-400 hover:text-accent hover:border-accent/40 transition-colors'
      >
        {collapsed ? <ChevronRight className='w-3 h-3' /> : <ChevronLeft className='w-3 h-3' />}
      </button>
    </motion.aside>
  )
}
