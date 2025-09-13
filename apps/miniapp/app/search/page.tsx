'use client';

import { useState } from 'react';
import Link from 'next/link';
import { t } from '@/lib/i18n';
import ReactMarkdown from 'react-markdown';
import { searchNotes } from '@/lib/api';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState('');
  const [items, setItems] = useState<Array<{ id: string; title: string }>>([]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await searchNotes(query);
    setAnswer(res.answer_md);
    setItems(res.items);
  };

  return (
    <main style={{ padding: '16px' }}>
      <h1 style={{ marginBottom: 8 }}>{t('search.title')}</h1>
      <form onSubmit={handleSearch} style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t('search.placeholder')}
          style={{ flex: 1 }}
        />
        <button type="submit">{t('search.button')}</button>
      </form>
      {answer && <ReactMarkdown>{answer}</ReactMarkdown>}
      {items.length > 0 && (
        <div>
          <h2 style={{ margin: '12px 0' }}>{t('search.results')}</h2>
          <ul>
            {items.map((note) => (
              <li key={note.id}>
                <Link href={`/notes/${note.id}`}>{note.title}</Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </main>
  );
}
