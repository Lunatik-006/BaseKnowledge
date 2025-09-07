import Link from 'next/link';
import { getNotes } from '@/lib/api';

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  const notes = await getNotes();
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
