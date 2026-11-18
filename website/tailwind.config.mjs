/** @type {import('tailwindcss').Config} */
const channel = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ['./src/**/*.{astro,tsx,ts,jsx,md,mdx}'],
  theme: {
    extend: {
      colors: {
        night: channel('bg'),
        panel: channel('surface'),
        panel2: channel('surface-2'),
        surface: channel('surface'),
        'surface-2': channel('surface-2'),
        line: channel('border'),
        ink: channel('text'),
        muted: channel('muted'),
        brand: channel('accent'),
        brand2: channel('accent-2'),
        mint: channel('success'),
        code: channel('code-bg'),
        codeink: channel('code-fg'),
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'SF Mono', 'Menlo', 'monospace'],
      },
      maxWidth: { content: '1200px' },
      boxShadow: {
        panel: '0 24px 70px -30px rgb(0 0 0 / .55)',
        lift: '0 18px 40px -24px rgb(var(--accent) / .55)',
      },
      borderRadius: { xl: '14px', '2xl': '20px' },
    },
  },
  plugins: [],
};
