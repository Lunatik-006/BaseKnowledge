'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { t } from '@/lib/i18n';
import { getNotes, getZipUrl } from '@/lib/api';

export default function HomePage() {
  const [notes, setNotes] = useState<Array<{ id: string; title: string }>>([]);

  useEffect(() => {
    getNotes().then(setNotes).catch(() => setNotes([]));
  }, []);

  return (
    <main style={{ padding: '16px' }}>
      <section style={{ margin: '8px 0 16px 0' }}>
        <h1 style={{ marginBottom: 8 }}>{t('home.title')}</h1>
        <p style={{ opacity: 0.85, marginBottom: 12 }}>
          {t('home.lead')}
        </p>
        <div style={{ display: 'flex', gap: 8 }}>
          <Link href="/search"><button>{t('home.cta.search')}</button></Link>
          <a href={getZipUrl()}><button>{t('home.cta.downloadZip')}</button></a>
        </div>
      </section>

      {notes.length > 0 ? (
        <section>
          <h2 style={{ margin: '12px 0' }}>{t('home.recent')}</h2>
          <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: 8 }}>
            {notes.map((note) => (
              <li key={note.id} style={{ border: '1px solid rgba(0,0,0,0.08)', borderRadius: 8, padding: 12 }}>
                <Link href={`/notes/${note.id}`}>{note.title}</Link>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <section style={{ opacity: 0.8, marginTop: 8 }}>
          <p>{t('home.noNotes')}</p>
        </section>
      )}
    </main>
  );
}
