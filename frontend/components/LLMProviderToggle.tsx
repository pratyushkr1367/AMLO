'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Cpu, Wifi, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import useSWR from 'swr'
import { fetcher } from '@/lib/api'

export function LLMProviderToggle() {
  const { data, mutate } = useSWR('/api/orchestration/llm-provider', fetcher, { refreshInterval: 10000 })
  const [switching, setSwitching] = useState(false)
  const [error, setError]         = useState<string | null>(null)

  const provider     = data?.provider ?? 'gemini'
  const isLocal      = provider === 'local'
  const geminiModel  = data?.gemini_model ?? 'gemini-2.0-flash-lite'
  const localModel   = data?.local_model  ?? 'gemma3:4b'

  const toggle = async () => {
    setSwitching(true)
    setError(null)
    const next = isLocal ? 'gemini' : 'local'
    try {
      const res = await fetch('/api/orchestration/llm-provider', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: next }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail ?? 'Switch failed')
      await mutate()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally {
      setSwitching(false)
    }
  }

  return (
    <div className='flex items-center gap-2'>
      <div className='flex items-center gap-1.5 text-[10px] font-mono text-slate-500'>
        {isLocal ? <Cpu className='w-3 h-3 text-status-normal' /> : <Wifi className='w-3 h-3 text-accent' />}
        <span className={isLocal ? 'text-status-normal' : 'text-accent'}>
          {isLocal ? localModel : geminiModel}
        </span>
      </div>

      <motion.button
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.97 }}
        onClick={toggle}
        disabled={switching || !data}
        title={`Switch to ${isLocal ? 'Gemini' : 'Local (Ollama)'}`}
        className={clsx(
          'relative flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-mono font-semibold border transition-colors',
          isLocal
            ? 'bg-status-normal/10 border-status-normal/20 text-status-normal hover:bg-status-normal/20'
            : 'bg-accent/10 border-accent/20 text-accent hover:bg-accent/20',
          (switching || !data) && 'opacity-50 cursor-not-allowed',
        )}
      >
        {switching
          ? <Loader2 className='w-3 h-3 animate-spin' />
          : isLocal ? <Cpu className='w-3 h-3' /> : <Wifi className='w-3 h-3' />
        }
        {isLocal ? 'LOCAL' : 'GEMINI'}
      </motion.button>

      <AnimatePresence>
        {error && (
          <motion.span
            initial={{ opacity: 0, x: -4 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0 }}
            className='text-[10px] font-mono text-status-critical'
          >
            {error}
          </motion.span>
        )}
      </AnimatePresence>
    </div>
  )
}
