/**
 * Deterministic, browser-only terminal state machine.
 *
 * The same reducer and renderer drive the homepage preview and the full
 * playground. It never executes shell commands and never touches the host.
 */
import { DEMO_AGENTS, DEMO_MCPS, DEMO_MODELS, DEMO_PRESETS, SITE } from './config';

export type Screen =
  | 'menu'
  | 'dashboard'
  | 'presets'
  | 'agents'
  | 'models'
  | 'fallbacks'
  | 'mcp'
  | 'config'
  | 'verify'
  | 'exit';

export type Action =
  | { type: 'up' | 'down' | 'enter' | 'esc' | 'reset' }
  | { type: 'char'; value: string }
  | { type: 'backspace' };

export interface State {
  screen: Screen;
  index: number;
  returnTo: Screen;
  preset: string;
  agent: string;
  mode: 'model' | 'fallback';
  assignments: Record<string, string>;
  fallbacks: Record<string, string>;
  mcp: Record<string, boolean>;
  search: string;
  notice: string;
}

const C = {
  reset: '\x1b[0m',
  boldCyan: '\x1b[1;36m',
  green: '\x1b[1;32m',
  yellow: '\x1b[33m',
  dim: '\x1b[2m',
  white: '\x1b[1;37m',
};

const MENU = [
  'Dashboard / overview',
  'Configure preset models',
  'Configure individual agents',
  'Browse & search models',
  'Manage fallbacks',
  'MCP servers',
  'Configuration preview',
  'Verify assignments',
  'Reset demonstration',
  'Exit demonstration',
] as const;

const key = (preset: string, agent: string) => `${preset}:${agent}`;

export function initialState(): State {
  const assignments: Record<string, string> = {};
  const fallbacks: Record<string, string> = {};
  DEMO_PRESETS.forEach((preset) => {
    DEMO_AGENTS.forEach((agent, index) => {
      assignments[key(preset, agent)] = DEMO_MODELS[index % DEMO_MODELS.length];
      if (index % 2 === 0) fallbacks[key(preset, agent)] = DEMO_MODELS[(index + 3) % DEMO_MODELS.length];
    });
  });
  const mcp: Record<string, boolean> = {};
  DEMO_MCPS.forEach((name) => { mcp[name] = true; });
  return {
    screen: 'menu',
    index: 0,
    returnTo: 'menu',
    preset: DEMO_PRESETS[0],
    agent: DEMO_AGENTS[0],
    mode: 'model',
    assignments,
    fallbacks,
    mcp,
    search: '',
    notice: 'Demo ready — no files or credentials are accessed.',
  };
}

export function options(state: State): string[] {
  switch (state.screen) {
    case 'menu': return [...MENU];
    case 'presets': return [...DEMO_PRESETS, '← Back'];
    case 'agents':
      return DEMO_AGENTS.map((agent) => `${agent}  [${state.assignments[key(state.preset, agent)]}]`).concat('← Back');
    case 'models': {
      const term = state.search.toLowerCase();
      const matches = DEMO_MODELS.filter((model) => model.toLowerCase().includes(term));
      return [...matches, '← Back'];
    }
    case 'fallbacks':
      return DEMO_AGENTS.map((agent) => `${agent}  [${state.fallbacks[key(state.preset, agent)] ?? 'none'}]`).concat('← Back');
    case 'mcp':
      return DEMO_MCPS.map((name) => `${name}  [${state.mcp[name] ? 'enabled' : 'disabled'}]`).concat('← Back');
    default: return [];
  }
}

function back(state: State): State {
  const map: Partial<Record<Screen, Screen>> = {
    presets: 'menu', agents: 'presets', models: state.returnTo,
    fallbacks: 'menu', mcp: 'menu', dashboard: 'menu', config: 'menu',
    verify: 'menu', exit: 'menu',
  };
  return { ...state, screen: map[state.screen] ?? 'menu', index: 0, search: '', notice: '' };
}

export function reduce(state: State, action: Action): State {
  switch (action.type) {
    case 'reset':
      return initialState();
    case 'up': {
      const length = options(state).length;
      return length ? { ...state, index: (state.index - 1 + length) % length } : state;
    }
    case 'down': {
      const length = options(state).length;
      return length ? { ...state, index: (state.index + 1) % length } : state;
    }
    case 'char':
      if (state.screen !== 'models' || action.value.length !== 1) return state;
      return { ...state, search: (state.search + action.value).slice(0, 40), index: 0 };
    case 'backspace':
      if (state.screen !== 'models') return state;
      return { ...state, search: state.search.slice(0, -1), index: 0 };
    case 'esc':
      if (state.search) return { ...state, search: '', index: 0 };
      return back(state);
    case 'enter': {
      const list = options(state);
      const selected = list[state.index];
      if (state.screen === 'menu') {
        switch (state.index) {
          case 0: return { ...state, screen: 'dashboard', index: 0, notice: '' };
          case 1: case 2: return { ...state, screen: 'presets', index: 0, notice: '' };
          case 3: return { ...state, screen: 'models', mode: 'model', returnTo: 'menu', index: 0, search: '', notice: '' };
          case 4: return { ...state, screen: 'fallbacks', index: 0, notice: '' };
          case 5: return { ...state, screen: 'mcp', index: 0, notice: '' };
          case 6: return { ...state, screen: 'config', index: 0, notice: '' };
          case 7: return { ...state, screen: 'verify', index: 0, notice: '' };
          case 8: return initialState();
          case 9: return { ...state, screen: 'exit', index: 0, notice: '' };
          default: return state;
        }
      }
      if (state.screen === 'presets') {
        if (selected === '← Back') return back(state);
        return { ...state, preset: selected, agent: DEMO_AGENTS[0], screen: 'agents', index: 0, notice: '' };
      }
      if (state.screen === 'agents') {
        if (selected === '← Back') return back(state);
        return { ...state, agent: selected.split('  [')[0], screen: 'models', mode: 'model', returnTo: 'agents', index: 0, search: '', notice: '' };
      }
      if (state.screen === 'fallbacks') {
        if (selected === '← Back') return back(state);
        return { ...state, agent: selected.split('  [')[0], screen: 'models', mode: 'fallback', returnTo: 'fallbacks', index: 0, search: '', notice: '' };
      }
      if (state.screen === 'models') {
        if (selected === '← Back') return back(state);
        const id = key(state.preset, state.agent);
        const updated = state.mode === 'fallback'
          ? { ...state.fallbacks, [id]: selected }
          : { ...state.assignments, [id]: selected };
        return {
          ...state,
          assignments: state.mode === 'model' ? updated : state.assignments,
          fallbacks: state.mode === 'fallback' ? updated : state.fallbacks,
          screen: state.returnTo,
          index: 0,
          search: '',
          notice: `${state.mode === 'fallback' ? 'Fallback' : 'Model'} set to ${selected} for ${state.preset}/${state.agent}`,
        };
      }
      if (state.screen === 'mcp') {
        if (selected === '← Back') return back(state);
        const name = selected.split('  [')[0];
        return { ...state, mcp: { ...state.mcp, [name]: !state.mcp[name] }, notice: `${name} ${state.mcp[name] ? 'disabled' : 'enabled'}` };
      }
      return back(state);
    }
    default:
      return state;
  }
}

function viewerLines(state: State): string[] {
  switch (state.screen) {
    case 'dashboard': {
      const used = new Set(Object.values(state.assignments));
      return [
        'DASHBOARD', '',
        `  Config:      ~/.config/opencode/oh-my-opencode-slim.json`,
        `  Active preset: ${state.preset}`,
        `  Assignments:  ${Object.keys(state.assignments).length}  ·  models in use: ${used.size}`,
        `  MCP servers:  ${Object.values(state.mcp).filter(Boolean).length} enabled`,
        '', '  Open an agent to change its model. Changes here are simulated.',
      ];
    }
    case 'config': {
      const preview = {
        preset: state.preset,
        presets: {
          [state.preset]: Object.fromEntries(
            DEMO_AGENTS.map((agent) => [
              agent,
              {
                model: state.assignments[key(state.preset, agent)],
                ...(state.fallbacks[key(state.preset, agent)]
                  ? { fallback_models: [state.fallbacks[key(state.preset, agent)]] }
                  : {}),
              },
            ]),
          ),
        },
        mcp: state.mcp,
      };
      return ['CONFIGURATION PREVIEW (simulated)', '', ...JSON.stringify(preview, null, 2).split('\n').map((line) => '  ' + line)];
    }
    case 'verify': {
      const models = new Set<string>(DEMO_MODELS);
      const rows = Object.entries(state.assignments)
        .filter(([id]) => id.startsWith(state.preset + ':'))
        .map(([id, model]) => `  ${models.has(model) ? '✓' : '✗'} ${id.replace(':', '/')}: ${model}`);
      return ['VERIFY ASSIGNMENTS (demo registry)', '', ...rows, '', `  ${rows.length} assignments checked.`];
    }
    case 'exit':
      return ['Session closed.', '', '  This was a browser simulation.', '  Press Enter or Esc to return to the menu.'];
    default:
      return [];
  }
}

export function render(state: State): string {
  const lines: string[] = [];
  lines.push(`${C.boldCyan}  OMO MANAGER  ·  v${SITE.version}  ·  INTERACTIVE DEMO${C.reset}`);
  lines.push(`${C.dim}  ${'─'.repeat(46)}${C.reset}`);
  lines.push(`  Preset: ${C.boldCyan}${state.preset}${C.reset}  ·  Agent: ${state.agent}`);
  if (state.screen === 'models') {
    lines.push(`  Model: ${state.assignments[key(state.preset, state.agent)]}`);
    lines.push(`  ${C.yellow}Search: ${state.search || '_'}${C.reset}`);
  } else {
    lines.push(`  Model: ${state.assignments[key(state.preset, state.agent)]}`);
  }
  lines.push('');

  const list = options(state);
  if (list.length) {
    if (state.screen === 'menu') lines.push(`  ${C.dim}CHOOSE AN ACTION${C.reset}`);
    list.forEach((option, index) => {
      const selected = index === state.index;
      lines.push(selected
        ? `${C.green}  ❯  ${option}${C.reset}`
        : `     ${option}`);
    });
  } else {
    lines.push(...viewerLines(state));
  }

  lines.push('');
  if (state.notice) lines.push(`  ${C.yellow}${state.notice}${C.reset}`);
  lines.push(`${C.dim}  ↑↓ select  ·  Enter open  ·  Esc back  ·  type to search${C.reset}`);
  lines.push(`${C.dim}  Browser simulation only — no local files, commands or credentials.${C.reset}`);
  return lines.join('\r\n') + '\r\n';
}

export function handleData(data: string, dispatch: (action: Action) => void): void {
  if (data.includes('[A') || data === 'k') dispatch({ type: 'up' });
  else if (data.includes('[B') || data === 'j') dispatch({ type: 'down' });
  else if (data.includes('[C') || data.includes('[D')) return;
  else if (data === '\r' || data === '\n') dispatch({ type: 'enter' });
  else if (data === '\x1b') dispatch({ type: 'esc' });
  else if (data === '\x7f' || data === '\b') dispatch({ type: 'backspace' });
  else if (data.length === 1 && data >= ' ' && data !== '\x00') dispatch({ type: 'char', value: data });
}
