const LEVELS: Record<string, number> = { debug: 10, info: 20, warn: 30, error: 40 };
const currentLevel = (process.env.LOG_LEVEL || 'info').toLowerCase();

function shouldLog(level: string): boolean {
  return LEVELS[level] >= LEVELS[currentLevel];
}

function format(level: string, args: unknown[]): string {
  const iso = new Date().toISOString(); // 2025-09-10T15:05:52.765Z
  const date = iso.slice(0, 10).replace(/-/g, '/');
  const time = iso.slice(11, 23);
  return `[${date} ${time} +00:00] [${level}] ${args
    .map((a) => (typeof a === 'string' ? a : JSON.stringify(a)))
    .join(' ')}`;
}

function log(level: keyof typeof LEVELS, args: unknown[]): void {
  if (!shouldLog(level)) return;
  process.stdout.write(format(level.toUpperCase(), args) + '\n');
}

export function setupLogger(): void {
  console.debug = (...args) => log('debug', args);
  console.info = (...args) => log('info', args);
  console.log = (...args) => log('info', args);
  console.warn = (...args) => log('warn', args);
  console.error = (...args) => log('error', args);
}

setupLogger();
