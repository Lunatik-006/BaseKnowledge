'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getNotes } from '@/lib/api';

export default function HomePage() {
  const [notes, setNotes] = useState<Array<{ id: string; title: string }>>([]);

  useEffect(() => {
    getNotes().then(setNotes).catch(() => setNotes([]));
  }, []);

  return (
    <main>
      <h1>Notes</h1>
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
