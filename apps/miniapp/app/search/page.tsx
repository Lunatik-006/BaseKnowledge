'use client';

import { useState } from 'react';
import Link from 'next/link';
import { searchNotes } from '@/lib/api';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Array<{id: string; title: string}>>([]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await searchNotes(query);
    setResults(res);
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
      <ul>
        {results.map((note) => (
          <li key={note.id}>
            <Link href={`/notes/${note.id}`}>{note.title}</Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
