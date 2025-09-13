export interface TelegramWebAppUser {
  language_code?: string;
}

export interface TelegramWebAppInitDataUnsafe {
  user?: TelegramWebAppUser;
}

export interface TelegramThemeParams {
  bg_color?: string;
  text_color?: string;
}

export interface TelegramWebApp {
  initData?: string;
  initDataUnsafe?: TelegramWebAppInitDataUnsafe;
  themeParams?: TelegramThemeParams;
  ready?: () => void;
  expand?: () => void;
  onEvent?: (event: 'themeChanged', cb: () => void) => void;
}

export function getWebApp(): TelegramWebApp | undefined {
  if (typeof window === 'undefined') return undefined;
  const w = window as unknown as { Telegram?: { WebApp?: TelegramWebApp } };
  return w.Telegram?.WebApp;
}

export function getInitData(): string | undefined {
  return getWebApp()?.initData;
}
