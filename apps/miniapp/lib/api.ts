const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function getNotes(): Promise<Array<{id: string; title: string}>> {
  const res = await fetch(`${API_BASE_URL}/notes`);
  if (!res.ok) {
    throw new Error('Failed to fetch notes');
  }
  return res.json();
}

export async function getNote(id: string): Promise<{id: string; title: string; content: string}> {
  const res = await fetch(`${API_BASE_URL}/notes/${id}`);
  if (!res.ok) {
    throw new Error('Failed to fetch note');
  }
  return res.json();
}

export async function searchNotes(query: string): Promise<Array<{id: string; title: string}>> {
  const res = await fetch(`${API_BASE_URL}/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) {
    throw new Error('Search request failed');
  }
  return res.json();
}

export function getZipUrl(id: string): string {
  return `${API_BASE_URL}/notes/${id}/zip`;
}

export function getObsidianUrl(id: string): string {
  return `obsidian://open?path=${encodeURIComponent(id)}`;
}
