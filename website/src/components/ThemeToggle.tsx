import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';

type Theme = 'dark' | 'light';

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>('dark');

  useEffect(() => {
    setTheme(document.documentElement.dataset.theme === 'light' ? 'light' : 'dark');
  }, []);

  function toggle() {
    const next: Theme = theme === 'light' ? 'dark' : 'light';
    setTheme(next);
    document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem('omo-theme', next); } catch { /* private mode */ }
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', next === 'light' ? '#f6f8fc' : '#070b16');
    window.dispatchEvent(new CustomEvent<Theme>('omo-theme-change', { detail: next }));
  }

  return (
    <button
      type="button"
      onClick={toggle}
      data-testid="theme-toggle"
      aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
      aria-pressed={theme === 'light'}
      title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
      className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-line bg-surface-2/70 text-muted hover:border-brand2/60 hover:text-ink"
    >
      {theme === 'light' ? <Moon size={18} aria-hidden="true" /> : <Sun size={18} aria-hidden="true" />}
    </button>
  );
}
