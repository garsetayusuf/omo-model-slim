import { useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { ChevronDown, FileText } from 'lucide-react';

export interface DocLink { slug: string; title: string; order: number }

interface Props { items: DocLink[]; current: string }

export default function DocsNav({ items, current }: Props) {
  const [open, setOpen] = useState(false);
  const reduced = useReducedMotion();
  const href = (slug: string) => (slug === 'index' ? '/docs' : `/docs/${slug}`);

  const nav = (
    <nav aria-label="Documentation sections" className="flex flex-col gap-1">
      {[...items].sort((a, b) => a.order - b.order).map((item) => (
        <a
          key={item.slug}
          href={href(item.slug)}
          aria-current={item.slug === current ? 'page' : undefined}
          onClick={() => setOpen(false)}
          className={`flex min-h-11 items-center gap-2 rounded-lg px-3 py-2 text-sm ${
            item.slug === current ? 'bg-brand/15 font-medium text-brand2' : 'text-muted hover:bg-panel2 hover:text-ink'
          }`}
        >
          <FileText size={15} aria-hidden="true" />
          {item.title}
        </a>
      ))}
    </nav>
  );

  return (
    <>
      <aside className="hidden w-60 shrink-0 lg:block" aria-label="Documentation navigation">
        <div className="sticky top-24">
          <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-widest text-muted">Documentation</p>
          {nav}
        </div>
      </aside>
      <div className="lg:hidden">
        <button
          type="button"
          aria-expanded={open}
          aria-controls="docs-mobile-nav"
          onClick={() => setOpen((value) => !value)}
          className="flex min-h-11 w-full items-center justify-between rounded-xl border border-line bg-panel px-4 text-sm text-ink"
          data-testid="docs-nav-toggle"
        >
          On this page<br /><span className="text-brand2">{items.find((item) => item.slug === current)?.title}</span>
          <ChevronDown size={18} aria-hidden="true" />
        </button>
        <AnimatePresence>
          {open && (
            <motion.div
              id="docs-mobile-nav"
              initial={reduced ? false : { height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={reduced ? undefined : { height: 0, opacity: 0 }}
              transition={{ duration: reduced ? 0 : 0.15 }}
              className="overflow-hidden"
            >
              <div className="mt-2 rounded-xl border border-line bg-panel p-2">{nav}</div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </>
  );
}
