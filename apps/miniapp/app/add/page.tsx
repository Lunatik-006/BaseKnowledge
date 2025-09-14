'use client';

import { useState } from 'react';
import { t } from '@/lib/i18n';
import { ingestAudio, ingestImage, ingestText, ingestVideo, IngestResult } from '@/lib/api';

type Tab = 'image' | 'audio' | 'text' | 'video';

export default function AddPage() {
  const [tab, setTab] = useState<Tab>('image');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [error, setError] = useState<string>('');
  const [text, setText] = useState<string>('');
  const [videoUrl, setVideoUrl] = useState<string>('');

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('loading');
    setError('');
    let res: IngestResult = { ok: false, error: 'not sent' };
    try {
      if (tab === 'image') {
        const file = (document.getElementById('image-input') as HTMLInputElement)?.files?.[0];
        if (!file) throw new Error('No file');
        res = await ingestImage(file);
      } else if (tab === 'audio') {
        const file = (document.getElementById('audio-input') as HTMLInputElement)?.files?.[0];
        if (!file) throw new Error('No file');
        res = await ingestAudio(file);
      } else if (tab === 'text') {
        res = await ingestText(text);
      } else if (tab === 'video') {
        res = await ingestVideo(videoUrl);
      }
    } catch (err: unknown) {
      const message = err instanceof Error
        ? err.message
        : 'Error';
      res = { ok: false, error: message };
    }
    if (res.ok) {
      setStatus('success');
      setText('');
      setVideoUrl('');
      try {
        const img = document.getElementById('image-input') as HTMLInputElement;
        const aud = document.getElementById('audio-input') as HTMLInputElement;
        if (img) img.value = '';
        if (aud) aud.value = '';
      } catch {}
    } else {
      setStatus('error');
      setError(res.error);
    }
  };

  const renderStatus = () => {
    if (status === 'idle') return null;
    if (status === 'loading') return <div style={{ padding: 8, border: '1px solid #eee', borderRadius: 8 }}>{t('add.status.loading')}</div>;
    if (status === 'success') return <div style={{ padding: 8, border: '1px solid #c8e6c9', background: '#e8f5e9', borderRadius: 8 }}>{t('add.status.success')}</div>;
    if (status === 'error') return <div style={{ padding: 8, border: '1px solid #ffcdd2', background: '#ffebee', borderRadius: 8 }}>{t('add.status.error')}: {error}</div>;
    return null;
  };

  const tabButton = (k: Tab, label: string) => (
    <button
      type="button"
      onClick={() => { setTab(k); setStatus('idle'); setError(''); }}
      style={{
        padding: '6px 10px',
        border: '1px solid rgba(0,0,0,0.1)',
        background: tab === k ? 'rgba(0,0,0,0.06)' : 'transparent',
        borderRadius: 6,
      }}
    >
      {label}
    </button>
  );

  return (
    <main style={{ padding: 16 }}>
      <h1 style={{ marginBottom: 8 }}>{t('add.title')}</h1>
      <p style={{ opacity: 0.85, marginBottom: 12 }}>{t('add.lead')}</p>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        {tabButton('image', t('add.tab.image'))}
        {tabButton('audio', t('add.tab.audio'))}
        {tabButton('text', t('add.tab.text'))}
        {tabButton('video', t('add.tab.video'))}
      </div>

      <form onSubmit={submit} style={{ display: 'grid', gap: 8 }}>
        {tab === 'image' && (
          <div style={{ display: 'grid', gap: 8 }}>
            <label htmlFor="image-input">{t('add.image.label')}</label>
            <input id="image-input" type="file" accept="image/*" />
            <small style={{ opacity: 0.8 }}>{t('add.image.hint')}</small>
          </div>
        )}
        {tab === 'audio' && (
          <div style={{ display: 'grid', gap: 8 }}>
            <label htmlFor="audio-input">{t('add.audio.label')}</label>
            <input id="audio-input" type="file" accept="audio/*" />
            <small style={{ opacity: 0.8 }}>{t('add.audio.hint')}</small>
          </div>
        )}
        {tab === 'text' && (
          <div style={{ display: 'grid', gap: 8 }}>
            <label htmlFor="text-input">{t('add.text.label')}</label>
            <textarea id="text-input" rows={6} value={text} onChange={(e) => setText(e.target.value)} placeholder={t('add.text.placeholder')} />
            <small style={{ opacity: 0.8 }}>{t('add.text.hint')}</small>
          </div>
        )}
        {tab === 'video' && (
          <div style={{ display: 'grid', gap: 8 }}>
            <label htmlFor="video-input">{t('add.video.label')}</label>
            <input id="video-input" value={videoUrl} onChange={(e) => setVideoUrl(e.target.value)} placeholder={t('add.video.placeholder')} />
            <small style={{ opacity: 0.8 }}>{t('add.video.hint')}</small>
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button type="submit" disabled={status === 'loading'}>
            {status === 'loading' ? t('add.submit.loading') : t('add.submit')}
          </button>
          {renderStatus()}
        </div>
      </form>
      <div style={{ marginTop: 12, opacity: 0.7, fontSize: 12 }}>
        {t('add.disclaimer')}
      </div>
    </main>
  );
}
