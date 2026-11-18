import { expect, test, type Page } from '@playwright/test';

const ROUTES = [
  { path: '/', heading: 'Your models.' },
  { path: '/docs', heading: 'Introduction' },
  { path: '/playground', heading: 'Interactive playground.' },
  { path: '/changelog', heading: 'Changelog.' },
];

async function paintedOpacity(page: Page): Promise<number> {
  return page.evaluate(() => {
    let node: HTMLElement | null = document.querySelector('h1');
    let value = 1;
    while (node && node !== document.body) {
      value *= Number.parseFloat(getComputedStyle(node).opacity);
      node = node.parentElement;
    }
    return value;
  });
}

for (const route of ROUTES) {
  test(`${route.path} renders its main content`, async ({ page }) => {
    await page.goto(route.path);
    await expect(page.locator('main')).toBeVisible();
    await expect(page.getByRole('heading', { level: 1 })).toContainText(route.heading);
    await expect(page.locator('footer')).toContainText('OMO Manager');
    await expect.poll(() => paintedOpacity(page), { timeout: 4000 }).toBeGreaterThan(0.99);
  });
}

test('hero content is actually painted (not left at opacity 0)', async ({ page }) => {
  await page.goto('/');
  await expect.poll(() => paintedOpacity(page), { timeout: 4000 }).toBeGreaterThan(0.99);
});

test('all four routes fit every target viewport without horizontal overflow', async ({ page }) => {
  for (const width of [320, 375, 390, 640, 768, 1024, 1280, 1440, 1920]) {
    await page.setViewportSize({ width, height: 900 });
    for (const route of ROUTES) {
      await page.goto(route.path);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow, `${route.path} overflows at ${width}px by ${overflow}px`).toBeLessThanOrEqual(1);
      const clipped = await page.evaluate(() => {
        const view = document.documentElement.clientWidth;
        return [...document.querySelectorAll('main a, main button, main code, main pre')].filter((el) => {
          const box = el.getBoundingClientRect();
          if (box.width === 0 || (box.left >= -1 && box.right <= view + 1)) return false;
          // Code inside a horizontally scrollable <pre> is intentional.
          let parent = el.parentElement;
          while (parent && parent !== document.body) {
            const overflow = getComputedStyle(parent).overflowX;
            if (overflow === 'auto' || overflow === 'scroll') return false;
            parent = parent.parentElement;
          }
          return true;
        }).length;
      });
      expect(clipped, `${route.path} has ${clipped} clipped interactive/code elements at ${width}px`).toBe(0);
    }
  }
});

test('FAQ opens only one answer at a time', async ({ page }) => {
  await page.goto('/');
  const faq = page.getByTestId('faq');
  await faq.scrollIntoViewIfNeeded();
  const buttons = faq.locator('button');
  await buttons.nth(0).click();
  await expect(buttons.nth(0)).toHaveAttribute('aria-expanded', 'true');
  await buttons.nth(1).click();
  await expect(buttons.nth(0)).toHaveAttribute('aria-expanded', 'false');
  await expect(buttons.nth(1)).toHaveAttribute('aria-expanded', 'true');
  await buttons.nth(1).click();
  await expect(buttons.nth(1)).toHaveAttribute('aria-expanded', 'false');
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

test('home terminal shows the full menu without truncation at 320px', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await page.goto('/');
  await expect(page.getByTestId('terminal').locator('.xterm')).toBeVisible();
  await expect.poll(async () => (await page.locator('.xterm-rows').first().textContent()) ?? '', { timeout: 4000 })
    .toContain('Exit demonstration');
  const text = (await page.locator('.xterm-rows').first().textContent()) ?? '';
  expect(text).not.toContain('more — resize');
  expect(text).toContain('OMO MANAGER');
});

test('terminal repaints one clean frame instead of stacking old screens', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId('terminal').locator('.xterm')).toBeVisible();
  for (let i = 0; i < 12; i += 1) await page.getByTestId('term-down').click();
  const text = await page.locator('.xterm-rows').first().textContent();
  expect((text?.match(/OMO MANAGER/g) ?? []).length).toBe(1);
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

test('theme toggle switches, persists and recolors the page', async ({ page }) => {
  await page.goto('/');
  const before = await page.evaluate(() => document.documentElement.dataset.theme);
  expect(['light', 'dark']).toContain(before);
  await page.getByTestId('theme-toggle').first().click();
  const after = await page.evaluate(() => document.documentElement.dataset.theme);
  expect(after).not.toBe(before);
  expect(await page.evaluate(() => localStorage.getItem('omo-theme'))).toBe(after);
  await page.reload();
  expect(await page.evaluate(() => document.documentElement.dataset.theme)).toBe(after);
  await expect.poll(
    () => page.evaluate(() => getComputedStyle(document.body).backgroundColor),
    { timeout: 3000 }
  ).toBe(after === 'light' ? 'rgb(246, 248, 252)' : 'rgb(7, 11, 22)');
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
