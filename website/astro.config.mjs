import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  site: 'https://omo-manager.seri.my.id',
  output: 'static',
  integrations: [
    react(),
    mdx(),
    tailwind({ applyBaseStyles: false }),
    sitemap({ changefreq: 'monthly', priority: 0.7 }),
  ],
  build: { inlineStylesheets: 'auto' },
});
