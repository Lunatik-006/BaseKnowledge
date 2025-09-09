'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getNotes, getZipUrl } from '@/lib/api';

export default function HomePage() {
  const [notes, setNotes] = useState<Array<{ id: string; title: string }>>([]);

  useEffect(() => {
    getNotes().then(setNotes).catch(() => setNotes([]));
  }, []);

  return (
    <main>
      <h1>Notes</h1>
      <a href={getZipUrl()}>
        <button>Download ZIP</button>
      </a>
      <ul>
        {notes.map((note) => (
          <li key={note.id}>
            <Link href={`/notes/${note.id}`}>{note.title}</Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
