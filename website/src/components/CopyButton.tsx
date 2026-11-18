import { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';

interface Props {
  text: string;
  label?: string;
  className?: string;
  testId?: string;
}

export default function CopyButton({ text, label = 'Copy', className = '', testId }: Props) {
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);
  const reduced = useReducedMotion();

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setFailed(false);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setFailed(true);
    }
  }

  return (
    <span className={`inline-flex flex-col items-end ${className}`}>
      <button
        type="button"
        onClick={copy}
        aria-label={`${label} to clipboard`}
        data-testid={testId}
        className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-line bg-panel2 px-3 text-xs font-medium text-ink hover:border-brand2/70 hover:bg-[#1a2740]"
      >
        <AnimatePresence mode="wait" initial={false}>
          <motion.span
            key={copied ? 'copied' : 'idle'}
            initial={reduced ? false : { opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={reduced ? undefined : { opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.15 }}
            className="inline-flex items-center gap-2"
          >
            {copied ? <Check size={14} className="text-mint" /> : <Copy size={14} />}
            {copied ? 'Copied' : label}
          </motion.span>
        </AnimatePresence>
      </button>
      <span aria-live="polite" className="sr-only">{copied ? 'Copied to clipboard' : ''}</span>
      {failed && <span className="mt-1 text-xs text-amber-300">Select the command and copy manually.</span>}
    </span>
  );
}
