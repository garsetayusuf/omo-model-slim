import { useEffect, useReducer, useRef, useState } from 'react';
import { RotateCcw } from 'lucide-react';
import type { ITheme, Terminal as TerminalType } from '@xterm/xterm';
import type { FitAddon as FitAddonType } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { handleData, initialState, reduce, render } from '../lib/terminal-engine';

interface Props {
  compact?: boolean;
  autoFocus?: boolean;
  title?: string;
}

type Theme = 'dark' | 'light';
const XTERM_THEME: Record<Theme, ITheme> = {
  dark: { background: '#080d18', foreground: '#dbe4f5', cursor: '#8b7cf6', selectionBackground: '#3b3168' },
  light: { background: '#eef2fa', foreground: '#1b2340', cursor: '#5b3fdc', selectionBackground: '#d8d3f8' },
};

export default function TerminalWindow({ compact = false, autoFocus = false, title = 'Interactive terminal' }: Props) {
  const [state, dispatch] = useReducer(reduce, undefined, initialState);
  const [ready, setReady] = useState(false);
  const [theme, setTheme] = useState<Theme>('dark');
  const mount = useRef<HTMLDivElement>(null);
  const terminal = useRef<TerminalType | null>(null);

  useEffect(() => {
    let live = true;
    let term: TerminalType | undefined;
    let fit: FitAddonType | undefined;
    let subscription: { dispose(): void } | undefined;
    let observer: ResizeObserver | undefined;

    (async () => {
      const [{ Terminal }, { FitAddon }] = await Promise.all([
        import('@xterm/xterm'),
        import('@xterm/addon-fit'),
      ]);
      if (!live || !mount.current) return;
      term = new Terminal({
        convertEol: true,
        cursorBlink: false,
        disableStdin: false,
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
        fontSize: compact ? (window.innerWidth < 640 ? 10 : 11) : window.innerWidth < 640 ? 11 : 13,
        lineHeight: 1.35,
        scrollback: 200,
        theme: XTERM_THEME.dark,
      });
      fit = new FitAddon();
      term.loadAddon(fit);
      term.open(mount.current);
      try { fit.fit(); } catch { /* container not measurable yet */ }
      terminal.current = term;
      subscription = term.onData((data) => handleData(data, dispatch));
      observer = new ResizeObserver(() => { try { fit?.fit(); } catch { /* ignore transient sizes */ } });
      observer.observe(mount.current);
      if (autoFocus) term.focus();
      setReady(true);
    })();

    return () => {
      live = false;
      setReady(false);
      observer?.disconnect();
      subscription?.dispose();
      term?.dispose();
      terminal.current = null;
    };
  }, [compact, autoFocus]);

  useEffect(() => {
    if (!ready || !terminal.current) return;
    const term = terminal.current;
    // Clear the viewport and scrollback: each state is a fresh screen, not a log.
    term.write('\x1b[H\x1b[2J\x1b[3J' + render(state, term.rows, term.cols));
  }, [state, ready]);

  useEffect(() => {
    const sync = () => setTheme(document.documentElement.dataset.theme === 'light' ? 'light' : 'dark');
    sync();
    window.addEventListener('omo-theme-change', sync);
    return () => window.removeEventListener('omo-theme-change', sync);
  }, []);

  useEffect(() => {
    if (ready && terminal.current) terminal.current.options.theme = XTERM_THEME[theme];
  }, [theme, ready]);

  const controls: Array<{ label: string; text: string; action: () => void; testId: string }> = [
    { label: 'Move selection up', text: '↑', action: () => dispatch({ type: 'up' }), testId: 'term-up' },
    { label: 'Move selection down', text: '↓', action: () => dispatch({ type: 'down' }), testId: 'term-down' },
    { label: 'Select current option', text: 'Enter', action: () => dispatch({ type: 'enter' }), testId: 'term-enter' },
    { label: 'Go back', text: 'Esc', action: () => dispatch({ type: 'esc' }), testId: 'term-esc' },
  ];

  return (
    <section className="surface min-w-0 max-w-full overflow-hidden shadow-panel" data-testid="terminal-window" aria-label={title}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-panel2/70 px-4 py-3">
        <span className="flex min-w-0 items-center gap-3 text-sm text-muted">
          <span aria-hidden="true" className="flex gap-1.5">
            <i className="h-2.5 w-2.5 rounded-full bg-[#ff6b6b]" />
            <i className="h-2.5 w-2.5 rounded-full bg-[#f7b955]" />
            <i className="h-2.5 w-2.5 rounded-full bg-[#4ade80]" />
          </span>
          <span className="min-w-0 truncate">{title}</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="rounded-full border border-brand/40 bg-brand/10 px-2.5 py-1 text-[11px] font-medium text-brand2" data-testid="terminal-status">
            {state.screen} · simulation
          </span>
          <button
            type="button"
            onClick={() => { dispatch({ type: 'reset' }); terminal.current?.focus(); }}
            aria-label="Reset demonstration"
            data-testid="term-reset"
            className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-line px-2.5 text-xs text-muted hover:border-brand2/60 hover:text-ink"
          >
            <RotateCcw size={13} /> Reset
          </button>
        </span>
      </div>
      <div
        ref={mount}
        role="application"
        aria-label="Interactive terminal simulation. Use arrow keys, Enter and Escape."
        tabIndex={0}
        data-testid="terminal"
        className={`w-full min-w-0 max-w-full overflow-hidden bg-code p-2 ${compact ? 'h-[360px] sm:h-[400px]' : 'h-[380px] sm:h-[480px]'}`}
        onClick={() => terminal.current?.focus()}
      />
      <div className="flex flex-wrap items-center gap-2 border-t border-line bg-panel2/50 px-4 py-3" aria-label="Touch terminal controls">
        {controls.map((control) => (
          <button
            key={control.testId}
            type="button"
            aria-label={control.label}
            data-testid={control.testId}
            onClick={control.action}
            className="min-h-11 min-w-[3.25rem] rounded-lg border border-line bg-panel2 px-3 text-sm font-medium text-ink hover:border-brand2/70 hover:bg-surface-2"
          >
            {control.text}
          </button>
        ))}
        <span className="ml-auto text-xs text-muted">Arrow keys · Enter · Esc</span>
      </div>
    </section>
  );
}
