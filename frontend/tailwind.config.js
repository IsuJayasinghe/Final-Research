/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // SmartYard dark theme (from the UI mockups)
        page: '#14233f',
        surface: '#1a2c4c',
        card: '#213659',
        line: '#33496f',
        muted: '#a3b3cd',
        ink: '#e6edf7',
        accent: { DEFAULT: '#22d3ee', strong: '#06b6d4', soft: '#0e3a4a' },
        ok: '#10b981',
        warn: '#f59e0b',
        danger: '#ef4444',
        // Yard zones
        zone: {
          fast: '#10b981',
          medium: '#f59e0b',
          long: '#38bdf8',
          reefer: '#22d3ee',
          hazard: '#ef4444',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
