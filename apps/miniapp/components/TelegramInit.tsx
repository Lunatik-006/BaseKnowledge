'use client';

import { useEffect } from 'react';
import WebApp from '@twa-dev/sdk';

export default function TelegramInit() {
  useEffect(() => {
    WebApp.ready();
  }, []);
  return null;
}
