'use client';

import { useEffect, useMemo, useState } from 'react';
import { t } from '@/lib/i18n';
import { getNotes } from '@/lib/api';
import Link from 'next/link';

type View = 'list' | 'grid';

export default function MyDataPage() {
  const [raw, setRaw] = useState<Array<{ id: string; title: string }>>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [query, setQuery] = useState<string>('');
  const [sort, setSort] = useState<'title-asc' | 'title-desc'>('title-asc');
  const [view, setView] = useState<View>('list');

  useEffect(() => {
    setLoading(true);
    getNotes()
      .then(setRaw)
      .finally(() => setLoading(false));
  }, []);

  const items = useMemo(() => {
    const q = query.trim().toLowerCase();
    let arr = raw.filter((n) => (q ? (n.title || '').toLowerCase().includes(q) : true));
    arr = arr.sort((a, b) => {
      if (sort === 'title-asc') return (a.title || '').localeCompare(b.title || '');
      return (b.title || '').localeCompare(a.title || '');
    });
    return arr;
  }, [raw, query, sort]);

  return (
    <main style={{ padding: 16 }}>
      <h1 style={{ marginBottom: 8 }}>{t('my.title')}</h1>
      <p style={{ opacity: 0.85, marginBottom: 12 }}>{t('my.lead')}</p>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t('my.search.placeholder')}
          style={{ flex: 1 }}
        />
        <select
          value={sort}
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
            setSort(e.target.value as 'title-asc' | 'title-desc')
          }
        >
          <option value="title-asc">{t('my.sort.titleAsc')}</option>
          <option value="title-desc">{t('my.sort.titleDesc')}</option>
        </select>
        <button type="button" onClick={() => setView(view === 'list' ? 'grid' : 'list')}>
          {view === 'list' ? t('my.view.grid') : t('my.view.list')}
        </button>
      </div>

      {loading ? (
        <div style={{ opacity: 0.8 }}>{t('status.loading')}</div>
      ) : items.length === 0 ? (
        <div style={{ opacity: 0.8 }}>{t('status.empty')}</div>
      ) : view === 'list' ? (
        <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: 8 }}>
          {items.map((n) => (
            <li key={n.id} style={{ border: '1px solid rgba(0,0,0,0.08)', borderRadius: 8, padding: 12 }}>
              <Link href={`/notes/${n.id}`}>{n.title}</Link>
            </li>
          ))}
        </ul>
      ) : (
        <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(2, 1fr)' }}>
          {items.map((n) => (
            <Link key={n.id} href={`/notes/${n.id}`} style={{
              border: '1px solid rgba(0,0,0,0.08)', borderRadius: 8, padding: 12,
              display: 'grid', gap: 6
            }}>
              <div style={{
                width: '100%', height: 80, borderRadius: 6,
                background: 'linear-gradient(135deg, rgba(0,0,0,0.05), rgba(0,0,0,0.08))'
              }} />
              <div style={{ fontWeight: 600, fontSize: 14 }}>{n.title}</div>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
