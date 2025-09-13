"use client";

import Link from "next/link";\nimport { t } from "@/lib/i18n";
import { getZipUrl } from "@/lib/api";

export default function Header() {
  return (
    <header style={{
      position: 'sticky', top: 0, zIndex: 10,
      backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)',
      background: 'rgba(0,0,0,0.03)',
      borderBottom: '1px solid rgba(0,0,0,0.06)',
      padding: '10px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between'
    }}>
      <Link href="/" style={{ fontWeight: 700 }}>BaseKnowledge</Link>
      <nav style={{ display: 'flex', gap: 8 }}>
        <Link href="/search"><button>{t("header.search")}</button></Link>
        <a href={getZipUrl()}><button>{t("header.downloadZip")}</button></a>
      </nav>
    </header>
  );
}

