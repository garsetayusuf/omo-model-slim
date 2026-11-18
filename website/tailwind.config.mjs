/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,tsx,ts,jsx,md,mdx}'],
  theme: {
    extend: {
      colors: {
        night: '#070b16',
        panel: '#0d1424',
        panel2: '#131d31',
        line: '#24304a',
        ink: '#e8edf7',
        muted: '#94a3b8',
        brand: '#8b7cf6',
        brand2: '#a78bfa',
        mint: '#34d399',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'SF Mono', 'Menlo', 'monospace'],
      },
      maxWidth: { content: '1200px' },
      boxShadow: {
        panel: '0 24px 70px -30px rgba(0,0,0,.85)',
        lift: '0 18px 40px -24px rgba(139,124,246,.55)',
      },
      borderRadius: { xl: '14px', '2xl': '20px' },
    },
  },
  plugins: [],
};
