import { chromium } from './grabadora.mjs';
const b = await chromium.launch({ executablePath: process.env.CHROME });
const p = await b.newPage({ viewport: { width: 512, height: 512 } });
await p.setContent(`<html><body style="margin:0;background:transparent">
<svg width="512" height="512" viewBox="0 0 512 512">
 <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2cc3b1"/><stop offset=".55" stop-color="#0d7f76"/><stop offset="1" stop-color="#075049"/></linearGradient>
 <linearGradient id="b" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".35"/><stop offset=".55" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>
 <rect x="16" y="16" width="480" height="480" rx="132" fill="url(#g)"/>
 <rect x="16" y="16" width="480" height="480" rx="132" fill="url(#b)"/>
 <path transform="translate(256 236) scale(8.4) translate(-16 -16)" d="M16 3.4c-6.1 0-10.6 3.3-10.6 8.9 0 3.9 1.1 6.9 1.9 10.9.6 3 1 5.8 3 5.8s2.4-2.7 3.1-5.5c.5-2 1.3-3.1 2.6-3.1s2.1 1.1 2.6 3.1c.7 2.8 1.1 5.5 3.1 5.5s2.4-2.8 3-5.8c.8-4 1.9-7 1.9-10.9 0-5.6-4.5-8.9-10.6-8.9Z" fill="#fff"/>
 <path d="M188 214 q68 58 136 0" stroke="#0d7f76" stroke-width="20" fill="none" stroke-linecap="round"/>
 <circle cx="368" cy="128" r="16" fill="#fff" opacity=".9"/><circle cx="398" cy="96" r="8" fill="#fff" opacity=".7"/>
</svg></body></html>`);
await p.screenshot({ path: 'logo-sonrisa.png', omitBackground: true });
await b.close();
