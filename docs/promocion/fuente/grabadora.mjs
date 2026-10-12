// Grabadora de tomas: captura con CDP (JPEG de alta calidad, cada cambio de
// pantalla con su marca de tiempo) y la convierte en un MP4 de 30 fps.
// Dibuja un cursor (o un toque, en celular) que se mueve con suavidad.
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';
const require = createRequire('/usr/lib/node_modules/n8n/node_modules/');
export const { chromium } = require('playwright-core');

const CURSOR = (tactil) => `
(() => {
  if (window.__cursor) return; window.__cursor = 1;
  const mk = () => {
    if (!document.body) return requestAnimationFrame(mk);
    const c = document.createElement('div');
    c.id = '__cur';
    c.style.cssText = 'position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;transition:opacity .2s;will-change:transform;opacity:0';
    c.innerHTML = ${tactil}
      ? '<div style="width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;background:rgba(255,255,255,.55);border:2px solid rgba(0,0,0,.25);box-shadow:0 4px 14px rgba(0,0,0,.25)"></div>'
      : '<svg width="30" height="30" viewBox="0 0 24 24" style="filter:drop-shadow(0 3px 5px rgba(0,0,0,.35))"><path d="M5 2.5v16.6l4.3-4.1 2.8 6.5 2.9-1.3-2.8-6.4h6z" fill="#111" stroke="#fff" stroke-width="1.4" stroke-linejoin="round"/></svg>';
    document.body.appendChild(c);
    const ring = (x, y) => {
      const r = document.createElement('div');
      r.style.cssText = 'position:fixed;z-index:2147483646;pointer-events:none;left:' + x + 'px;top:' + y + 'px;width:16px;height:16px;margin:-8px 0 0 -8px;border-radius:50%;border:3px solid rgba(13,127,118,.85);background:rgba(13,127,118,.18);transition:transform .45s cubic-bezier(.2,.8,.2,1),opacity .45s';
      document.body.appendChild(r);
      requestAnimationFrame(() => { r.style.transform = 'scale(3.4)'; r.style.opacity = '0'; });
      setTimeout(() => r.remove(), 520);
    };
    addEventListener('pointermove', (e) => { c.style.opacity = 1; c.style.transform = 'translate(' + e.clientX + 'px,' + e.clientY + 'px)'; }, true);
    addEventListener('pointerdown', (e) => { ring(e.clientX, e.clientY); c.firstChild.style.transform = 'scale(.85)'; }, true);
    addEventListener('pointerup', () => { c.firstChild.style.transform = ''; }, true);
  };
  mk();
})();`;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

export async function abrir({ ancho, alto, escala = 1, movil = false, oscuro = false }) {
  const navegador = await chromium.launch({ executablePath: process.env.CHROME, args: ['--force-color-profile=srgb', '--font-render-hinting=none'] });
  const ctx = await navegador.newContext({
    viewport: { width: ancho, height: alto }, deviceScaleFactor: escala, isMobile: movil, hasTouch: movil,
    colorScheme: oscuro ? 'dark' : 'light', locale: 'es-EC', timezoneId: 'America/Guayaquil',
  });
  await ctx.addInitScript(CURSOR(movil));
  await ctx.addInitScript(() => { window.print = () => {}; });
  const p = await ctx.newPage();
  p.__pos = { x: ancho * 0.6, y: alto * 0.55 };
  return { navegador, ctx, p };
}

/** Mueve el cursor con una curva suave hasta (x, y). */
export async function mover(p, x, y, ms = 650) {
  const { x: x0, y: y0 } = p.__pos;
  // Por tiempo real: si un paso tarda, el siguiente se adelanta.
  const t0 = Date.now();
  for (;;) {
    const f = Math.min(1, (Date.now() - t0) / ms);
    const k = ease(f);
    await p.mouse.move(x0 + (x - x0) * k, y0 + (y - y0) * k);
    if (f >= 1) break;
    await sleep(12);
  }
  p.__pos = { x, y };
}

export async function centro(loc) {
  await loc.scrollIntoViewIfNeeded().catch(() => {});
  const b = await loc.boundingBox();
  if (!b) throw new Error('sin caja: ' + loc);
  return [b.x + b.width / 2, b.y + b.height / 2];
}

export async function clic(p, loc, { ms = 650, pausa = 350 } = {}) {
  const [x, y] = await centro(loc);
  await mover(p, x, y, ms);
  await sleep(120);
  await p.mouse.down(); await sleep(70); await p.mouse.up();
  await sleep(pausa);
}

export async function tocar(p, x, y, pausa = 450) {
  await mover(p, x, y, 420);
  await p.mouse.down(); await sleep(80); await p.mouse.up();
  await sleep(pausa);
}

export async function escribir(p, texto, ms = 55) {
  for (const ch of texto) { await p.keyboard.type(ch); await sleep(ms + Math.random() * 40); }
}

/** Desplazamiento suave con la rueda. */
export async function rueda(p, dy, ms = 1200) {
  const t0 = Date.now(); let hecho = 0;
  for (;;) {
    const f = Math.min(1, (Date.now() - t0) / ms);
    const objetivo = Math.round(dy * ease(f));
    if (objetivo !== hecho) { await p.mouse.wheel(0, objetivo - hecho); hecho = objetivo; }
    if (f >= 1) break;
    await sleep(16);
  }
}

/** Arrastre táctil (scroll en el celular). */
export async function deslizar(p, x, y0, y1, ms = 600) {
  await mover(p, x, y0, 300);
  await p.mouse.down();
  const t0 = Date.now();
  for (;;) { const f = Math.min(1, (Date.now() - t0) / ms); await p.mouse.move(x, y0 + (y1 - y0) * ease(f)); if (f >= 1) break; await sleep(12); }
  await p.mouse.up(); p.__pos = { x, y: y1 };
}

export { sleep };

/** Graba lo que pase dentro de `accion` en `salida` (mp4). */
export async function grabar(p, salida, accion, { ancho, alto, fps = 30 } = {}) {
  const dir = salida + '.frames';
  fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true });
  const cdp = await p.context().newCDPSession(p);
  const cuadros = [];
  cdp.on('Page.screencastFrame', async (f) => {
    const n = cuadros.length;
    const archivo = path.join(dir, String(n).padStart(6, '0') + '.jpg');
    fs.writeFileSync(archivo, Buffer.from(f.data, 'base64'));
    cuadros.push({ archivo, t: f.metadata.timestamp });
    cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }).catch(() => {});
  });
  await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: ancho, maxHeight: alto, everyNthFrame: 1 });
  const t0 = Date.now() / 1000;
  await sleep(300);
  await accion();
  await sleep(400);
  const t1 = Date.now() / 1000;
  await cdp.send('Page.stopScreencast');
  await sleep(200);
  if (!cuadros.length) throw new Error('sin cuadros');
  // Lista con duraciones reales entre cuadros (la pantalla quieta no envía cuadros).
  let lista = 'ffconcat version 1.0\n';
  for (let i = 0; i < cuadros.length; i++) {
    const fin = i + 1 < cuadros.length ? cuadros[i + 1].t : t1;
    const ini = i === 0 ? Math.min(cuadros[0].t, t0) : cuadros[i].t;
    lista += `file '${path.basename(cuadros[i].archivo)}'\nduration ${Math.max(0.001, fin - ini).toFixed(4)}\n`;
  }
  lista += `file '${path.basename(cuadros.at(-1).archivo)}'\n`;
  fs.writeFileSync(path.join(dir, 'lista.txt'), lista);
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', path.join(dir, 'lista.txt'),
    '-vf', `fps=${fps},scale=${ancho}:${alto}:flags=lanczos,format=yuv420p`, '-c:v', 'libx264', '-preset', 'slow', '-crf', '15',
    '-movflags', '+faststart', salida]);
  fs.rmSync(dir, { recursive: true, force: true });
  const dur = execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', salida]).toString().trim();
  console.log(`  ${path.basename(salida)}  ${Number(dur).toFixed(1)} s  (${cuadros.length} cuadros)`);
}

/** Para páginas creadas con setContent, donde el script inicial no corre. */
export async function ponerCursor(p, tactil = false) { await p.evaluate(CURSOR(tactil)); }
