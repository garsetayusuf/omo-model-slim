import { useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { Plus } from 'lucide-react';

export interface FaqItem { q: string; a: string }

export default function Faq({ items }: { items: FaqItem[] }) {
  const [open, setOpen] = useState<number | null>(null);
  const reduced = useReducedMotion();

  return (
    <div className="mt-8 grid gap-4 lg:grid-cols-2" data-testid="faq">
      {items.map((item, index) => {
        const active = open === index;
        return (
          <div key={item.q} className="surface overflow-hidden">
            <h3>
              <button
                type="button"
                id={`faq-button-${index}`}
                aria-expanded={active}
                aria-controls={`faq-panel-${index}`}
                onClick={() => setOpen(active ? null : index)}
                className="flex min-h-14 w-full items-center justify-between gap-4 px-5 py-4 text-left font-medium text-ink"
              >
                <span>{item.q}</span>
                <motion.span
                  aria-hidden="true"
                  className="shrink-0 text-brand2"
                  animate={{ rotate: active ? 45 : 0 }}
                  transition={{ duration: reduced ? 0 : 0.18 }}
                >
                  <Plus size={18} />
                </motion.span>
              </button>
            </h3>
            <AnimatePresence initial={false}>
              {active && (
                <motion.div
                  id={`faq-panel-${index}`}
                  role="region"
                  aria-labelledby={`faq-button-${index}`}
                  initial={reduced ? false : { height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={reduced ? undefined : { height: 0, opacity: 0 }}
                  transition={{ duration: reduced ? 0 : 0.2 }}
                  className="overflow-hidden"
                >
                  <p className="px-5 pb-5 text-sm leading-6 text-muted">{item.a}</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
}
