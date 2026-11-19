// Tomas sin edición, pero presentadas dentro de los dispositivos con el mismo
// diseño del video de lanzamiento: la web en la laptop, la app en el celular
// (con barra de estado, sin nada tapado por la isla) y en la tablet.
// Cada toma va completa, sin cortes ni textos. Salida: ../tomas-sin-edicion.mp4
//
//   CHROME=.../chrome node tomas-en-dispositivos.mjs
import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';
import { fileURLToPath } from 'url';
import { chromium } from './grabadora.mjs';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const TMP = path.join(AQUI, 'tmp-dispositivos');
fs.mkdirSync(TMP, { recursive: true });

const FONDO = '#081011', CUERPO = '#0d1314', ARO = '#2f3b3c';

// Geometría (1920×1080).
const LAP = { x: 240, y: 121, w: 1440, h: 810 };
const TAB = { x: 320, y: 140, w: 1280, h: 800 };
const INT = 400, BARRA = Math.round(INT * 0.14), PIE = Math.round(INT * 0.075), APP_H = Math.round(INT / 0.4619);
const TEL = { x: 760, w: INT, h: APP_H + BARRA + PIE };
TEL.y = Math.round((1080 - TEL.h) / 2);

const iconos = (c) => `<svg width="17" height="11" viewBox="0 0 17 11"><g fill="${c}"><rect x="0" y="7" width="3" height="4" rx="1"/><rect x="4.5" y="5" width="3" height="6" rx="1"/><rect x="9" y="2.5" width="3" height="8.5" rx="1"/><rect x="13.5" y="0" width="3" height="11" rx="1"/></g></svg>
<svg width="15" height="11" viewBox="0 0 15 11"><path fill="${c}" d="M7.5 2.2c2 0 3.9.8 5.3 2.1l1.1-1.1A9 9 0 0 0 7.5.6 9 9 0 0 0 1.1 3.2l1.1 1.1A7.5 7.5 0 0 1 7.5 2.2Zm0 3.1c1.2 0 2.3.4 3.1 1.2l1.1-1.1a6 6 0 0 0-8.4 0l1.1 1.1c.8-.8 1.9-1.2 3.1-1.2Zm0 3.1c-.4 0-.8.2-1.1.5L7.5 10l1.1-1.1c-.3-.3-.7-.5-1.1-.5Z"/></svg>
<svg width="25" height="12" viewBox="0 0 25 12"><rect x=".5" y=".5" width="21" height="11" rx="3" fill="none" stroke="${c}" stroke-opacity=".45"/><rect x="2" y="2" width="16" height="8" rx="1.8" fill="${c}"/><rect x="22.8" y="4" width="1.6" height="4" rx=".8" fill="${c}" fill-opacity=".5"/></svg>`;

const hueco = (r, radio, aros) => `<div style="position:absolute;left:${r.x}px;top:${r.y}px;width:${r.w}px;height:${r.h}px;border-radius:${radio}px;box-shadow:${aros},0 0 0 4000px ${FONDO}"></div>`;

const marcos = {
  laptop: hueco(LAP, 3, `0 0 0 14px ${CUERPO},0 0 0 15.5px ${ARO}`) +
    `<div style="position:absolute;left:${LAP.x + LAP.w / 2 - 2.5}px;top:${LAP.y - 10}px;width:5px;height:5px;border-radius:50%;background:#26302f"></div>
     <div style="position:absolute;left:${LAP.x - 14 - 74}px;top:${LAP.y + LAP.h + 16}px;width:${LAP.w + 28 + 148}px;height:20px;border-radius:2px 2px 18px 18px;background:#20292a;box-shadow:inset 0 2px 0 #3a4647,inset 0 -3px 6px rgba(0,0,0,.5)">
       <div style="margin:0 auto;width:15%;height:6px;border-radius:0 0 8px 8px;background:#111819"></div></div>`,
  tablet: hueco(TAB, 20, `0 0 0 14px ${CUERPO},0 0 0 15.5px ${ARO}`),
};
for (const [nombre, c] of [['tel-oscuro', '#14242b'], ['tel-claro', '#ffffff']]) {
  marcos[nombre] = hueco(TEL, 44, `0 0 0 9px ${CUERPO},0 0 0 10.5px ${ARO}`) +
    `<div style="position:absolute;left:${TEL.x}px;top:${TEL.y}px;width:${TEL.w}px;height:${BARRA}px;display:flex;align-items:center;justify-content:space-between;padding:0 9% 0 11%;box-sizing:border-box;font:600 15px 'Inter',sans-serif;letter-spacing:-.01em;color:${c}">
       <span>9:41</span><span style="display:flex;align-items:center;gap:5px">${iconos(c)}</span></div>
     <div style="position:absolute;left:${TEL.x + TEL.w * 0.35}px;top:${TEL.y + Math.round(BARRA * 0.28)}px;width:${TEL.w * 0.3}px;height:${Math.round(BARRA * 0.5)}px;border-radius:15px;background:${CUERPO}"></div>
     <div style="position:absolute;left:${TEL.x + TEL.w * 0.33}px;top:${TEL.y + TEL.h - 11}px;width:${TEL.w * 0.34}px;height:4px;border-radius:3px;background:${c};opacity:${c === '#ffffff' ? 0.7 : 0.35}"></div>`;
}

const navegador = await chromium.launch({ executablePath: process.env.CHROME, args: ['--force-color-profile=srgb', '--font-render-hinting=none'] });
const pagina = await navegador.newPage({ viewport: { width: 1920, height: 1080 } });
for (const [nombre, html] of Object.entries(marcos)) {
  await pagina.setContent(`<!doctype html><html><head><link href="https://fonts.googleapis.com/css2?family=Inter:wght@600&display=block" rel="stylesheet">
    <style>html,body{margin:0;background:transparent;overflow:hidden}</style></head><body>${html}</body></html>`, { waitUntil: 'networkidle' });
  await pagina.evaluate(() => document.fonts.ready);
  await pagina.screenshot({ path: path.join(TMP, `${nombre}.png`), omitBackground: true });
}
await navegador.close();

// Orden de las tomas. En el celular, tramos con fondo oscuro → barra en blanco.
const TOMAS = [
  ['web-02-panel', 'laptop'], ['web-03-agenda', 'laptop'], ['web-04-paciente', 'laptop'],
  ['web-05-odontograma', 'laptop'], ['web-08-finanzas', 'laptop'], ['web-20-facturas', 'laptop'],
  ['web-21-emitir', 'laptop'], ['web-22-firma', 'laptop'], ['movil-23-firma', 'tel'],
  ['app-20-login', 'tel', [1.4, 12.1]], ['app-21-glass', 'tel'], ['app-22-ficha', 'tel'],
  ['app-23-sin-red', 'tel'], ['app-24-tablet', 'tablet'],
];

const partes = [];
for (const [n, disp, oscuro] of TOMAS) {
  const ent = path.join(AQUI, 'tomas', `${n}.mp4`), sal = path.join(TMP, `${n}.mp4`);
  let filtro, marcosIn;
  if (disp === 'tel') {
    const claro = oscuro ? `between(t,${oscuro[0]},${oscuro[1]})` : '0';
    filtro = `[0:v]split[a][b];` +
      `[a]scale=${TEL.w}:${TEL.h}:force_original_aspect_ratio=increase,crop=${TEL.w}:${TEL.h},boxblur=22:2[fondo];` +
      `[b]scale=${TEL.w}:${APP_H}[app];[fondo][app]overlay=0:${BARRA}[pant];` +
      `color=${FONDO}:s=1920x1080:r=30[lienzo];[lienzo][pant]overlay=${TEL.x}:${TEL.y}:shortest=1[c];` +
      `[c][1:v]overlay=0:0:enable='not(${claro})'[d];[d][2:v]overlay=0:0:enable='${claro}',format=yuv420p[o]`;
    marcosIn = ['-i', path.join(TMP, 'tel-oscuro.png'), '-i', path.join(TMP, 'tel-claro.png')];
  } else {
    const r = disp === 'laptop' ? LAP : TAB;
    filtro = `[0:v]scale=${r.w}:${r.h}[pant];color=${FONDO}:s=1920x1080:r=30[lienzo];[lienzo][pant]overlay=${r.x}:${r.y}:shortest=1[c];[c][1:v]overlay=0:0,format=yuv420p[o]`;
    marcosIn = ['-i', path.join(TMP, `${disp}.png`)];
  }
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', ent, ...marcosIn, '-filter_complex', filtro,
    '-map', '[o]', '-r', '30', '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-shortest', sal], { stdio: 'inherit' });
  partes.push(sal);
  console.log('listo', n);
}

fs.writeFileSync(path.join(TMP, 'lista.txt'), partes.map((p) => `file '${p}'`).join('\n'));
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', path.join(TMP, 'lista.txt'),
  '-c', 'copy', '-movflags', '+faststart', path.join(AQUI, '..', 'tomas-sin-edicion.mp4')], { stdio: 'inherit' });
fs.rmSync(TMP, { recursive: true, force: true });
console.log('Hecho: ../tomas-sin-edicion.mp4');
