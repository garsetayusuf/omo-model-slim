import { expect, test } from '@playwright/test';

const ROUTES = [
  { path: '/', heading: 'Your models.' },
  { path: '/docs', heading: 'Introduction' },
  { path: '/playground', heading: 'Interactive playground.' },
  { path: '/changelog', heading: 'Changelog.' },
];

for (const route of ROUTES) {
  test(`${route.path} renders its main content`, async ({ page }) => {
    await page.goto(route.path);
    await expect(page.locator('main')).toBeVisible();
    await expect(page.getByRole('heading', { level: 1 })).toContainText(route.heading);
    await expect(page.locator('footer')).toContainText('OMO Manager');
  });
}

test('all four routes have no horizontal overflow at narrow widths', async ({ page }) => {
  for (const width of [320, 375, 390, 640, 768]) {
    await page.setViewportSize({ width, height: 800 });
    for (const route of ROUTES) {
      await page.goto(route.path);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow, `${route.path} overflows at ${width}px by ${overflow}px`).toBeLessThanOrEqual(1);
    }
  }
});

test('installation command is copyable', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('/');
  const command = page.getByTestId('install-text');
  await expect(command).toContainText('curl -fsSL');
  await page.getByTestId('install-copy').click();
  await expect(page.getByTestId('install-copy')).toContainText('Copied');
  const clip = await page.evaluate(() => navigator.clipboard.readText());
  expect(clip).toContain('raw.githubusercontent.com/garsetayusuf/omo-model-slim');
});

test('terminal initializes and responds to keyboard navigation', async ({ page }) => {
  await page.goto('/playground');
  const term = page.getByTestId('terminal');
  await expect(term.locator('.xterm')).toBeVisible();
  await expect(page.getByTestId('terminal-status')).toContainText('menu');
  await term.click();
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('Enter');
  await expect(page.getByTestId('terminal-status')).toContainText('presets');
});

test('terminal touch controls navigate and change a model', async ({ page }) => {
  await page.goto('/playground');
  await expect(page.getByTestId('terminal').locator('.xterm')).toBeVisible();
  await expect(page.getByTestId('term-enter')).toBeEnabled();
  await page.getByTestId('term-enter').click(); // menu -> dashboard
  await expect(page.getByTestId('terminal-status')).toContainText('dashboard');
  await page.getByTestId('term-esc').click(); // -> menu
  await page.getByTestId('term-down').click(); // index 1: presets
  await page.getByTestId('term-enter').click(); // -> presets
  await page.getByTestId('term-enter').click(); // -> agents
  await page.getByTestId('term-enter').click(); // -> models
  await expect(page.getByTestId('terminal-status')).toContainText('models');
  await page.getByTestId('term-down').click(); // second model
  await page.getByTestId('term-enter').click(); // apply -> agents
  await expect(page.getByTestId('terminal-status')).toContainText('agents');
});

test('terminal reset restores the initial state', async ({ page }) => {
  await page.goto('/playground');
  await page.getByTestId('term-enter').click();
  await expect(page.getByTestId('terminal-status')).toContainText('dashboard');
  await page.getByTestId('term-reset').click();
  await expect(page.getByTestId('terminal-status')).toContainText('menu');
});

test('documentation search and mobile drawer work', async ({ page }) => {
  await page.goto('/docs');
  await expect(page.getByTestId('docs-nav-toggle')).toBeAttached(); // island hydrated
  await page.getByTestId('docs-search').fill('MCP');
  await expect(page.getByRole('link', { name: /MCP servers/i }).first()).toBeVisible();

  await page.setViewportSize({ width: 375, height: 800 });
  await page.getByTestId('docs-nav-toggle').click();
  await expect(page.getByRole('navigation', { name: 'Documentation sections' })).toBeVisible();
});

test('reduced motion is honored', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  const reduced = await page.evaluate(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  expect(reduced).toBeTruthy();
  await expect(page.getByRole('heading', { level: 1 })).toContainText('One terminal.');
});

test('pages expose accessible landmarks and named controls', async ({ page }) => {
  await page.goto('/playground');
  await expect(
    page.getByRole('navigation', { name: 'Main navigation' }).or(page.getByTestId('nav-toggle')).first()
  ).toBeVisible();
  await expect(page.getByRole('button', { name: 'Reset demonstration' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Move selection down' })).toBeVisible();
});
