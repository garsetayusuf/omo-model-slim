import { useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { Menu, X } from 'lucide-react';
import { NAV, SITE } from '../lib/config';

interface Props { pathname: string }

export default function SiteNav({ pathname }: Props) {
  const [open, setOpen] = useState(false);
  const reduced = useReducedMotion();
  const links = NAV.map((item) => ({ ...item, active: item.href === pathname }));

  return (
    <header className="sticky top-0 z-50 border-b border-line/70 bg-night/85 backdrop-blur-xl">
      <div className="container-page flex h-16 items-center justify-between gap-4">
        <a href="/" className="flex items-center gap-2 text-base font-bold tracking-tight text-ink" onClick={() => setOpen(false)}>
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand/20 font-mono text-sm text-brand2">⌘</span>
          OMO <span className="text-brand2">Manager</span>
        </a>
        <nav aria-label="Main navigation" className="hidden items-center gap-1 md:flex">
          {links.map((item) => (
            <a
              key={item.label}
              href={item.href}
              target={item.external ? '_blank' : undefined}
              rel={item.external ? 'noopener noreferrer' : undefined}
              aria-current={item.active ? 'page' : undefined}
              className={`rounded-lg px-3 py-2 text-sm ${item.active ? 'bg-panel2 text-ink' : 'text-muted hover:bg-panel2/60 hover:text-ink'}`}
            >
              {item.label}{item.external ? ' ↗' : ''}
            </a>
          ))}
          <a href="#install" className="btn-primary ml-2 hidden lg:inline-flex">Install</a>
        </nav>
        <button
          type="button"
          aria-label={open ? 'Close navigation menu' : 'Open navigation menu'}
          aria-expanded={open}
          aria-controls="mobile-navigation"
          onClick={() => setOpen((value) => !value)}
          className="grid h-11 w-11 place-items-center rounded-lg border border-line text-ink md:hidden"
          data-testid="nav-toggle"
        >
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>
      <AnimatePresence>
        {open && (
          <motion.nav
            id="mobile-navigation"
            aria-label="Mobile navigation"
            initial={reduced ? false : { height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={reduced ? undefined : { height: 0, opacity: 0 }}
            transition={{ duration: reduced ? 0 : 0.15 }}
            className="overflow-hidden border-t border-line bg-panel md:hidden"
          >
            <div className="container-page flex flex-col py-3">
              {links.map((item) => (
                <a
                  key={item.label}
                  href={item.href}
                  target={item.external ? '_blank' : undefined}
                  rel={item.external ? 'noopener noreferrer' : undefined}
                  onClick={() => setOpen(false)}
                  aria-current={item.active ? 'page' : undefined}
                  className="min-h-12 rounded-lg px-3 py-3 text-sm text-ink hover:bg-panel2"
                >
                  {item.label}{item.external ? ' ↗' : ''}
                </a>
              ))}
              <p className="px-3 pb-2 pt-4 text-xs text-muted">OMO Manager v{SITE.version} · browser simulation only</p>
            </div>
          </motion.nav>
        )}
      </AnimatePresence>
    </header>
  );
}
