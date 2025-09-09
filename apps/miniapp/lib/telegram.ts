export function getInitData(): string | undefined {
  if (typeof window !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return (window as any).Telegram?.WebApp?.initData as string | undefined;
  }
  return undefined;
}
