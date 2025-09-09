'use client';

import { useEffect, useState } from 'react';
import { getNote, getZipUrl, getObsidianUrl } from '@/lib/api';

export default function NotePage({ params }: { params: { id: string } }) {
  const { id } = params;
  const [note, setNote] = useState<{ id: string; title: string; content: string } | null>(null);

  useEffect(() => {
    getNote(id).then(setNote).catch(() => setNote(null));
  }, [id]);

  if (!note) {
    return <main>Loading...</main>;
  }

  return (
    <main>
      <h1>{note.title}</h1>
      <pre>{note.content}</pre>
      <div style={{ marginTop: '1rem' }}>
        <a href={getZipUrl(id)}>
          <button>Download ZIP</button>
        </a>
        <a href={getObsidianUrl(id)} style={{ marginLeft: '0.5rem' }}>
          <button>Open in Obsidian</button>
        </a>
      </div>
    </main>
  );
}
