'use client';

import { useEffect } from 'react';

export default function TelegramInit() {
  useEffect(() => {
    import('@twa-dev/sdk').then((mod) => {
      mod.default.ready();
    });
  }, []);
  return null;
}
