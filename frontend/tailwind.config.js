/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // SmartYard dark theme (from the UI mockups)
        page: '#0b1424',
        surface: '#111c30',
        card: '#16233b',
        line: '#24344f',
        muted: '#8b9bb7',
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
