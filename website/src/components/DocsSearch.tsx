import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import type { DocLink } from './DocsNav';

interface Props { items: (DocLink & { description?: string })[] }

export default function DocsSearch({ items }: Props) {
  const [query, setQuery] = useState('');
  const results = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return [];
    return items
      .filter((item) => `${item.title} ${item.description ?? ''}`.toLowerCase().includes(term))
      .slice(0, 7);
  }, [items, query]);

  const href = (slug: string) => (slug === 'index' ? '/docs' : `/docs/${slug}`);

  return (
    <div className="relative mb-8">
      <label className="sr-only" htmlFor="docs-search">Search documentation</label>
      <Search size={16} aria-hidden="true" className="pointer-events-none absolute left-3 top-3.5 text-muted" />
      <input
        id="docs-search"
        data-testid="docs-search"
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search documentation…"
        className="min-h-11 w-full rounded-xl border border-line bg-panel py-3 pl-10 pr-4 text-sm text-ink placeholder:text-muted focus:border-brand2"
      />
      {results.length > 0 && (
        <ul className="absolute z-20 mt-2 w-full overflow-hidden rounded-xl border border-line bg-panel2 shadow-panel" role="listbox">
          {results.map((item) => (
            <li key={item.slug} role="option" aria-selected="false">
              <a href={href(item.slug)} className="block px-4 py-3 text-sm text-ink hover:bg-brand/15">
                {item.title}
                {item.description && <span className="block truncate text-xs text-muted">{item.description}</span>}
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
