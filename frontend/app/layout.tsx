import type { Metadata } from 'next'
import './globals.css'
import { Sidebar } from '@/components/Sidebar'

export const metadata: Metadata = {
  title: 'AMLO — Autonomous Maintenance & Logistics Orchestrator',
  description: 'Factory intelligence dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang='en'>
      <body className='flex h-screen overflow-hidden bg-surface-0'>
        <Sidebar />
        <main className='flex-1 overflow-auto bg-grid-pattern bg-grid'>
          {children}
        </main>
      </body>
    </html>
  )
}
