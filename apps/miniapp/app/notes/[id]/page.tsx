import { getNote, getZipUrl, getObsidianUrl } from '@/lib/api';

export default async function NotePage({ params }: { params: { id: string } }) {
  const note = await getNote(params.id);
  return (
    <main>
      <h1>{note.title}</h1>
      <pre>{note.content}</pre>
      <div style={{ marginTop: '1rem' }}>
        <a href={getZipUrl(params.id)}>
          <button>Download ZIP</button>
        </a>
        <a href={getObsidianUrl(params.id)} style={{ marginLeft: '0.5rem' }}>
          <button>Open in Obsidian</button>
        </a>
      </div>
    </main>
  );
}
