"use client";

import { use, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { getNote, getZipUrl, getObsidianUrl } from "@/lib/api";
import { t } from "@/lib/i18n";

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
          <button>{t('note.downloadZip')}</button>
        </a>
        <a href={getObsidianUrl(slug)} style={{ marginLeft: "0.5rem" }}>
          <button>{t('note.openInObsidian')}</button>
        </a>
      </div>
    </main>
  );
}
