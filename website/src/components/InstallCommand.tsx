import { useState } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import CopyButton from './CopyButton';
import { SITE } from '../lib/config';

const PLATFORMS = [
  { id: 'macOS', hint: 'Run in Terminal or iTerm2 on macOS. Apple Silicon and Intel are supported.' },
  { id: 'Linux', hint: 'Run in your Linux terminal. Ubuntu, Debian, and Fedora are supported.' },
  { id: 'WSL', hint: 'Run inside your WSL Linux shell — not PowerShell or Command Prompt.' },
] as const;

export default function InstallCommand() {
  const [platform, setPlatform] = useState<(typeof PLATFORMS)[number]['id']>('macOS');
  const reduced = useReducedMotion();
  const hint = PLATFORMS.find((entry) => entry.id === platform)!.hint;

  return (
    <div className="surface p-5 sm:p-6" data-testid="install-command">
      <div className="mb-4 flex flex-wrap gap-2" role="tablist" aria-label="Install platform">
        {PLATFORMS.map((entry) => (
          <button
            key={entry.id}
            type="button"
            role="tab"
            aria-selected={platform === entry.id}
            onClick={() => setPlatform(entry.id)}
            className={`relative min-h-10 rounded-lg px-4 text-sm font-medium ${platform === entry.id ? 'text-white' : 'text-muted hover:text-ink'}`}
          >
            {platform === entry.id && !reduced && (
              <motion.span layoutId="install-tab" className="absolute inset-0 rounded-lg bg-brand/90" transition={{ duration: 0.18 }} />
            )}
            {platform === entry.id && reduced && <span className="absolute inset-0 rounded-lg bg-brand/90" />}
            <span className="relative">{entry.id}</span>
          </button>
        ))}
      </div>
      <p className="mb-4 text-sm text-muted">{hint} Requires Python 3.10+ and curl. No sudo required.</p>
      <div className="flex items-start gap-3 rounded-xl border border-line bg-code p-4">
        <code className="min-w-0 flex-1 break-all font-mono text-[13px] leading-6 text-codeink" data-testid="install-text">
          {SITE.install}
        </code>
        <CopyButton text={SITE.install} testId="install-copy" />
      </div>
      <p className="mt-4 text-xs text-muted">
        Installs to <code className="text-codeink">~/.local/bin/omo-model-slim</code>. Your existing{' '}
        <code className="text-codeink">omo-model</code> is never modified.
      </p>
    </div>
  );
}
