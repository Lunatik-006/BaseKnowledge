import { getNote, getZipUrl, getObsidianUrl } from '@/lib/api';

export default async function NotePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const note = await getNote(id);
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
