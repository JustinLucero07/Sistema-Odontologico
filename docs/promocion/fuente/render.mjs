// node render.mjs <anuncio|teaser> <h|v> [--muestras t1,t2,...] [--contacto "..."]
import { chromium } from './grabadora.mjs';
import fs from 'fs';
import { spawn } from 'child_process';
const [v, f] = process.argv.slice(2);
const arg = (n) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : null; };
const muestras = arg('--muestras');
const contacto = arg('--contacto') || 'Escríbenos por WhatsApp';
const TOTALES = Object.fromEntries(fs.readdirSync('cuadros').map((d) => [d, fs.readdirSync('cuadros/' + d).length]));
const b = await chromium.launch({ executablePath: process.env.CHROME, args: ['--force-color-profile=srgb'] });
const W = f === 'v' ? 1080 : 1920, H = f === 'v' ? 1920 : 1080;
const p = await b.newPage({ viewport: { width: W, height: H } });
p.on('pageerror', (e) => console.error('ERROR', e.message));
await p.addInitScript((t) => { window.TOTALES = t; }, TOTALES);
const CAMP = v === 'campana';
await p.goto(`http://localhost:5077/${CAMP ? 'campana' : 'film'}.html?f=${f}&v=${v}&c=${encodeURIComponent(CAMP ? (arg('--contacto') || '') : contacto)}`);
await p.evaluate((c) => { window.OBJ = c ? window.CAMPANA : window.FILM; }, CAMP);
await p.evaluate(() => document.fonts.ready);
await new Promise((r) => setTimeout(r, 800));
const dur = await p.evaluate(() => OBJ.dur);
if (muestras) {
  for (const t of muestras.split(',').map(Number)) {
    await p.evaluate((t) => OBJ.render(t), t);
    await p.screenshot({ path: `muestra-${v}-${f}-${t}.jpg`, type: 'jpeg', quality: 85 });
  }
  await b.close(); process.exit(0);
}
const salida = `${v}-${f}-sin-audio.mp4`;
const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', '30', '-c:v', 'mjpeg', '-i', '-',
  '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', salida], { stdio: ['pipe', 'inherit', 'inherit'] });
const N = Math.round(dur * 30);
const t0 = Date.now();
for (let i = 0; i < N; i++) {
  await p.evaluate((t) => OBJ.render(t), i / 30);
  const img = await p.screenshot({ type: 'jpeg', quality: 94 });
  if (!ff.stdin.write(img)) await new Promise((r) => ff.stdin.once('drain', r));
  if (i % 150 === 0) console.log(`  ${v}-${f}: ${i}/${N} (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
}
ff.stdin.end();
await new Promise((r) => ff.on('close', r));
await b.close();
console.log('listo', salida);
