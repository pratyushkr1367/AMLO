import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        surface: {
          0: '#04060e',
          1: '#080d18',
          2: '#0c1220',
          3: '#111827',
          4: '#1a2438',
        },
        border: {
          DEFAULT: '#1e2d42',
          bright: '#2a3f5c',
        },
        accent: {
          DEFAULT: '#38bdf8',
          dim: '#0ea5e9',
          glow: 'rgba(56,189,248,0.15)',
        },
        status: {
          normal:    '#4ade80',
          degrading: '#fbbf24',
          critical:  '#f87171',
          offline:   '#64748b',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 2.5s cubic-bezier(0.4,0,0.6,1) infinite',
        'glow-red': 'glowRed 1.5s ease-in-out infinite',
        'glow-amber': 'glowAmber 2s ease-in-out infinite',
        'scan': 'scan 4s linear infinite',
      },
      keyframes: {
        glowRed: {
          '0%,100%': { boxShadow: '0 0 4px 1px rgba(248,113,113,0.2)' },
          '50%':     { boxShadow: '0 0 16px 4px rgba(248,113,113,0.5)' },
        },
        glowAmber: {
          '0%,100%': { boxShadow: '0 0 4px 1px rgba(251,191,36,0.15)' },
          '50%':     { boxShadow: '0 0 12px 3px rgba(251,191,36,0.4)' },
        },
        scan: {
          '0%':   { backgroundPosition: '0% 0%' },
          '100%': { backgroundPosition: '0% 100%' },
        },
      },
      backgroundImage: {
        'grid-pattern': `linear-gradient(rgba(30,45,66,0.4) 1px, transparent 1px),
                         linear-gradient(90deg, rgba(30,45,66,0.4) 1px, transparent 1px)`,
      },
      backgroundSize: {
        'grid': '32px 32px',
      },
    },
  },
  plugins: [],
}

export default config
