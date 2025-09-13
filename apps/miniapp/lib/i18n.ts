export type Lang = 'en' | 'ru';

import en from '@/locales/en.json';
import ru from '@/locales/ru.json';

function normalize(lang?: string | null): Lang {
  const l = (lang || '').toLowerCase();
  return l.startsWith('ru') ? 'ru' : 'en';
}

export function getLang(): Lang {
  if (typeof window === 'undefined') return 'en';
  const url = new URL(window.location.href);
  const lp = url.searchParams.get('lang');
  if (lp) return normalize(lp);
  const ls = window.localStorage?.getItem('lang');
  if (ls) return normalize(ls);
  const tg = (window as any).Telegram?.WebApp?.initDataUnsafe?.user?.language_code as string | undefined;
  if (tg) return normalize(tg);
  return 'en';
}

export function setLang(lang: string) {
  const l = normalize(lang);
  if (typeof window !== 'undefined') {
    window.localStorage?.setItem('lang', l);
    document.documentElement.lang = l;
  }
}

const DICTS: Record<Lang, Record<string, string>> = {
  en: en as Record<string, string>,
  ru: ru as Record<string, string>,
};

export function t(key: string): string {
  const l = getLang();
  const dict = DICTS[l] || DICTS.en;
  return dict[key] || key;
}
