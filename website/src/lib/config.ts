export const SITE = {
  name: 'OMO Manager',
  version: '1.0.6',
  description:
    'Manage OpenCode and Oh My OpenCode Slim models, presets, providers, and MCP servers without manually editing JSON.',
  repo: 'https://github.com/garsetayusuf/omo-model-slim',
  website: 'https://omo-manager.seri.my.id',
  install: 'curl -fsSL https://raw.githubusercontent.com/garsetayusuf/omo-model-slim/main/install.sh | bash',
} as const;

export const NAV: ReadonlyArray<{ label: string; href: string; external?: boolean }> = [
  { label: 'Docs', href: '/docs' },
  { label: 'Playground', href: '/playground' },
  { label: 'Changelog', href: '/changelog' },
  { label: 'GitHub', href: SITE.repo, external: true },
] as const;

// Demo-only data used by the browser terminal simulator.
export const DEMO_PRESETS = ['openai', 'opencode-go', 'balanced'] as const;
export const DEMO_AGENTS = ['orchestrator', 'oracle', 'explorer', 'designer', 'fixer'] as const;
export const DEMO_MODELS = [
  'openai/gpt-6.1-sol',
  'openai/gpt-6-luna',
  'opencode-go/minimax-m3',
  'opencode-go/kimi-k2.7-code',
  'anthropic/claude-sonnet-4.5',
  'google/gemini-3-flash',
  'groq/llama-3.3-70b-versatile',
] as const;
export const DEMO_MCPS = ['context7', 'gh_grep', 'webfetch', 'filesystem'] as const;
