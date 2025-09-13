'use client';

import { useEffect } from 'react';
import { getWebApp, TelegramWebApp } from '@/lib/telegram';

export default function TelegramInit() {
  useEffect(() => {
    import('@twa-dev/sdk').then((mod) => {
      const tg = mod.default;
      tg.ready();
      try { tg.expand(); } catch {}
      // Language detection from URL and Telegram, stored to localStorage
      try {
        const url = new URL(window.location.href);
        const ql = url.searchParams.get('lang');
        if (ql) {
          window.localStorage.setItem('lang', ql.toLowerCase().startsWith('ru') ? 'ru' : 'en');
        }
        const ls = window.localStorage.getItem('lang');
        if (!ls) {
          const code = getWebApp()?.initDataUnsafe?.user?.language_code;
          if (code) {
            window.localStorage.setItem('lang', code.toLowerCase().startsWith('ru') ? 'ru' : 'en');
          }
        }
        const cur = window.localStorage.getItem('lang') || 'en';
        document.documentElement.lang = cur;
      } catch {}
      const applyTheme = () => {
        const wp: TelegramWebApp | undefined = getWebApp();
        const tp = wp?.themeParams || {};
        const root = document.documentElement;
        if (tp.bg_color) root.style.setProperty('--background', tp.bg_color);
        if (tp.text_color) root.style.setProperty('--foreground', tp.text_color);
      };
      applyTheme();
      getWebApp()?.onEvent?.('themeChanged', applyTheme);
    });
  }, []);
  return null;
}
