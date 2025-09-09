"use client";

import { use, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { getNote, getZipUrl, getObsidianUrl } from "@/lib/api";

export default function NotePage({ params }: { params: Promise<{ id: string }> }) {
  const { id: slug } = use(params);
  const [note, setNote] = useState<
    { id: string; title: string; content: string } | null
  >(null);

  useEffect(() => {
    getNote(slug)
      .then(setNote)
      .catch(() => setNote(null));
  }, [slug]);

  if (!note) {
    return <main>Loading...</main>;
  }

  return (
    <main>
      <h1>{note.title}</h1>
      <ReactMarkdown>{note.content}</ReactMarkdown>
      <div style={{ marginTop: "1rem" }}>
        <a href={getZipUrl()}>
          <button>Download ZIP</button>
        </a>
        <a href={getObsidianUrl(slug)} style={{ marginLeft: "0.5rem" }}>
          <button>Open in Obsidian</button>
        </a>
      </div>
    </main>
  );
}
