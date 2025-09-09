'use client';

import { useState } from 'react';
import Link from 'next/link';
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
    <main>
      <h1>Search</h1>
      <form onSubmit={handleSearch}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search notes"
        />
        <button type="submit">Search</button>
      </form>
      {answer && <ReactMarkdown>{answer}</ReactMarkdown>}
      {items.length > 0 && (
        <div>
          <h2>См. также</h2>
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
