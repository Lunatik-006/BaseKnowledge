import { getInitData } from './telegram';

// Compute API base URL:
// - In browser: same-origin '/api' behind nginx (avoids hardcoded localhost)
// - On server or when PUBLIC_URL is provided at build time: use PUBLIC_URL
// - Fallback for local dev: http://localhost:8000
const PUBLIC_URL = process.env.PUBLIC_URL;
const API_BASE_URL =
  typeof window !== 'undefined'
    ? `${window.location.origin.replace(/\/$/, '')}/api`
    : PUBLIC_URL
    ? `${PUBLIC_URL.replace(/\/$/, '')}/api`
    : 'http://localhost:8000';

function authHeaders(extra: HeadersInit = {}): HeadersInit {
  const initData = getInitData();
  return initData ? { 'X-Telegram-Init-Data': initData, ...extra } : extra;
}

export async function getNotes(): Promise<Array<{id: string; title: string}>> {
  try {
    const res = await fetch(`${API_BASE_URL}/notes`, { headers: authHeaders() });
    if (!res.ok) {
      throw new Error('Failed to fetch notes');
    }
    return res.json();
  } catch (err) {
    console.error('Error fetching notes', err);
    return [];
  }
}

export async function getNote(id: string): Promise<{id: string; title: string; content: string}> {
  const res = await fetch(`${API_BASE_URL}/notes/${id}`, { headers: authHeaders() });
  if (!res.ok) {
    throw new Error('Failed to fetch note');
  }
  return res.json();
}

export async function searchNotes(
  query: string,
): Promise<{ answer_md: string; items: Array<{ id: string; title: string }> }> {
  const res = await fetch(`${API_BASE_URL}/search`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ query }),
  });
  if (!res.ok) {
    throw new Error('Search request failed');
  }
  const data = await res.json();
  return {
    answer_md: data.answer_md,
    items: data.items.map(
      (item: { note_id: string; title: string }) => ({
        id: item.note_id,
        title: item.title,
      }),
    ),
  };
}

export function getZipUrl(): string {
  const initData = getInitData();
  const url = `${API_BASE_URL}/export/zip`;
  return initData ? `${url}?initData=${encodeURIComponent(initData)}` : url;
}

export function getObsidianUrl(slug: string): string {
  return `obsidian://${slug}`;
}
