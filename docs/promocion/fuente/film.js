// Película animada cuadro a cuadro. FILM.render(t) deja el escenario en el
// instante t (segundos) y espera a que las imágenes estén decodificadas.
// Parámetros: ?f=h|v (horizontal/vertical) &v=anuncio|teaser &c=contacto
const Q = new URLSearchParams(location.search);
const F = Q.get('f') || 'h';
const V = Q.get('v') || 'anuncio';
const CONTACTO = Q.get('c') || 'Escríbenos por WhatsApp';
const VERT = F === 'v';
const W = VERT ? 1080 : 1920, H = VERT ? 1920 : 1080;
const FPS = 30;
const stage = document.getElementById('stage');
stage.style.width = W + 'px'; stage.style.height = H + 'px';

// ---------- utilidades ----------
const cl = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, k) => a + (b - a) * k;
const E = {
  lin: (t) => t,
  out: (t) => 1 - Math.pow(1 - t, 3),
  out5: (t) => 1 - Math.pow(1 - t, 5),
  expo: (t) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t)),
  inn: (t) => t * t * t,
  io: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  back: (t) => { const c = 1.5, c3 = c + 1; return 1 + c3 * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); },
  // Muelle amortiguado: rebote suave al llegar.
  spring: (t) => (t >= 1 ? 1 : 1 - Math.exp(-6.5 * t) * Math.cos(9 * t)),
};
const pr = (lt, s, d, e = E.out) => e(cl((lt - s) / d));
const h = (html) => { const d = document.createElement('div'); d.innerHTML = html.trim(); return d.firstElementChild; };
function pon(el, o = {}) {
  const { x = 0, y = 0, s = 1, sx, sy, r = 0, rx = 0, ry = 0, o: op = 1, b = 0, z = 0 } = o;
  el.style.transform = `translate3d(${x}px,${y}px,${z}px) perspective(2000px) rotateX(${rx}deg) rotateY(${ry}deg) rotate(${r}deg) scale(${sx ?? s},${sy ?? s})`;
  el.style.opacity = op;
  el.style.filter = b > 0.05 ? `blur(${b}px)` : 'none';
}
const ruido = (n) => { const x = Math.sin(n * 12.9898) * 43758.5453; return x - Math.floor(x); };

// ---------- íconos (Material) ----------
const IC = {
  agenda: 'M17 12h-5v5h5v-5zM16 1v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2h-1V1h-2zm3 18H5V8h14v11z',
  chat: 'M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 9h12v2H6V9zm8 5H6v-2h8v2zm4-6H6V6h12v2z',
  billetera: 'M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8zm4-2.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z',
  grafico: 'M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z',
  recibo: 'M18 17H6v-2h12v2zm0-4H6v-2h12v2zm0-4H6V7h12v2zM3 22l1.5-1.5L6 22l1.5-1.5L9 22l1.5-1.5L12 22l1.5-1.5L15 22l1.5-1.5L18 22l1.5-1.5L21 22V2l-1.5 1.5L18 2l-1.5 1.5L15 2l-1.5 1.5L12 2l-1.5 1.5L9 2 7.5 3.5 6 2 4.5 3.5 3 2v20z',
  paleta: 'M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9c.83 0 1.5-.67 1.5-1.5 0-.39-.15-.74-.39-1.01-.23-.26-.38-.61-.38-.99 0-.83.67-1.5 1.5-1.5H16c2.76 0 5-2.24 5-5 0-4.42-4.03-8-9-8zm-5.5 9c-.83 0-1.5-.67-1.5-1.5S5.67 9 6.5 9 8 9.67 8 10.5 7.33 12 6.5 12zm3-4C8.67 8 8 7.33 8 6.5S8.67 5 9.5 5s1.5.67 1.5 1.5S10.33 8 9.5 8zm5 0c-.83 0-1.5-.67-1.5-1.5S13.67 5 14.5 5s1.5.67 1.5 1.5S15.33 8 14.5 8zm3 4c-.83 0-1.5-.67-1.5-1.5S16.67 9 17.5 9s1.5.67 1.5 1.5-.67 1.5-1.5 1.5z',
  celular: 'M17 1.01L7 1c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14z',
  papel: 'M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z',
  tabla: 'M10 10.02h5V21h-5zM17 21h3c1.1 0 2-.9 2-2v-9h-5v11zm3-18H5c-1.1 0-2 .9-2 2v3h19V5c0-1.1-.9-2-2-2zM3 19c0 1.1.9 2 2 2h3V10H3v9z',
  dinero: 'M19 14V6c0-1.1-.9-2-2-2H3c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zm-9-1c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm13-6v11c0 1.1-.9 2-2 2H4v-2h17V7h2z',
  flecha: 'M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z',
  cerrar: 'M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z',
  ok: 'M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z',
  persona: 'M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z',
  equipo: 'M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z',
  clinica: 'M19 3H5c-1.1 0-1.99.9-1.99 2L3 19c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-1 11h-4v4h-4v-4H6v-4h4V6h4v4h4v4z',
  escudo: 'M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z',
  nube: 'M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM10 17l-3.5-3.5 1.41-1.41L10 14.17 15.18 9l1.41 1.41L10 17z',
  dispositivos: 'M4 6h18V4H4c-1.1 0-2 .9-2 2v11H0v3h14v-3H4V6zm19 2h-6c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h6c.55 0 1-.45 1-1V9c0-.55-.45-1-1-1zm-1 9h-4v-7h4v7z',
  reloj: 'M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z',
  diente: 'M12 2.6c-4.6 0-7.9 2.5-7.9 6.7 0 2.9.8 5.2 1.4 8.2.5 2.2.8 4.3 2.3 4.3s1.8-2 2.3-4.1c.4-1.5 1-2.3 1.9-2.3s1.5.8 1.9 2.3c.5 2.1.8 4.1 2.3 4.1s1.8-2.1 2.3-4.3c.6-3 1.4-5.3 1.4-8.2 0-4.2-3.3-6.7-7.9-6.7z',
  candado: 'M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z',
};
const svg = (n, t, color = '#fff') => `<svg viewBox="0 0 24 24" width="${t}" height="${t}" style="fill:${color}"><path d="${IC[n]}"/></svg>`;
const icono = (n, t = 72, fondo) => `<span class="icono" style="width:${t}px;height:${t}px;border-radius:${Math.round(t * 0.3)}px;${fondo ? `background:${fondo}` : ''}">${svg(n, Math.round(t * 0.52))}</span>`;
const MARCA = (t) => `<span class="icono" style="width:${t}px;height:${t}px;border-radius:${Math.round(t * 0.3)}px">
  <svg viewBox="0 0 24 24" width="${Math.round(t * 0.6)}" height="${Math.round(t * 0.6)}"><path fill="#fff" d="${IC.diente}"/><path d="M8.6 9.6q3.4 2.8 6.8 0" stroke="#0d7f76" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg></span>`;

// ---------- clips de video (secuencias de cuadros) ----------
const pendientes = [];
class Clip {
  constructor(nombre, total) { this.nombre = nombre; this.total = total; this.img = document.createElement('img'); this.n = 0; }
  ir(seg) {
    const n = cl(Math.floor(seg * FPS) + 1, 1, this.total);
    if (n !== this.n) {
      this.n = n;
      this.img.src = `cuadros/${this.nombre}/${String(n).padStart(5, '0')}.jpg`;
      pendientes.push(this.img.decode().catch(() => {}));
    }
  }
}
const TOTALES = window.TOTALES || {};
const clip = (n) => new Clip(n, TOTALES[n] || 300);

function ventana(c, ancho, recorte) {
  const el = h(`<div class="abs ventana vidrio" style="width:${ancho}px">
    <div class="barra"><b style="background:#ff5f57"></b><b style="background:#febc2e"></b><b style="background:#28c840"></b>
    <span class="url">${svg('candado', 13, '#9fd8cf')}app.tuconsultorio.com</span></div></div>`);
  if (recorte) {
    // Zoom a la zona importante: la pantalla se ve grande en el celular.
    const { alto, zoom, fx, fy } = recorte;
    const marco = h(`<div style="position:relative;height:${alto}px;overflow:hidden"></div>`);
    const anchoImg = ancho * zoom, altoImg = anchoImg * 9 / 16;
    c.img.style.cssText = `position:absolute;width:${anchoImg}px;height:${altoImg}px;max-width:none;left:${-(anchoImg - ancho) * fx}px;top:${-(altoImg - alto) * fy}px`;
    marco.appendChild(c.img); el.appendChild(marco);
  } else el.appendChild(c.img);
  return el;
}
function telefono(c, alto) {
  const ancho = Math.round(alto * 0.4618);
  const el = h(`<div class="abs telefono" style="width:${ancho}px;height:${alto}px"><div class="pantalla" style="width:100%;height:100%"><div class="isla"></div></div></div>`);
  el.firstElementChild.appendChild(c.img);
  return el;
}

// Texto que entra palabra por palabra.
function texto(html, clase, estilo) {
  const el = h(`<div class="abs ${clase}" style="${estilo}"></div>`);
  const tmp = document.createElement('div'); tmp.innerHTML = html;
  const piezas = [];
  // El degradado (oro/menta) se pone en cada palabra: un background-clip:text
  // del padre no alcanza a hijos transformados.
  const recorrer = (nodo, destino, extra = '') => {
    for (const n of [...nodo.childNodes]) {
      if (n.nodeType === 3) {
        n.textContent.split(/(\s+)/).forEach((p) => {
          if (!p) return;
          if (/^\s+$/.test(p)) { destino.appendChild(document.createTextNode(' ')); return; }
          const s = document.createElement('span'); s.className = 'palabra ' + extra; s.textContent = p; destino.appendChild(s); piezas.push(s);
        });
      } else if (n.nodeName === 'BR') destino.appendChild(document.createElement('br'));
      else {
        const grad = ['oro', 'menta'].filter((k) => n.classList?.contains(k));
        const c = n.cloneNode(false); grad.forEach((k) => c.classList.remove(k));
        destino.appendChild(c); recorrer(n, c, (extra + ' ' + grad.join(' ')).trim());
      }
    }
  };
  recorrer(tmp, el);
  el.piezas = piezas;
  return el;
}
// Animación estándar de entrada/salida por palabras.
function animarTexto(el, lt, ini, { paso = 0.06, dur = 0.55, dy = 60, blur = 14, salida = null, ds = 0 } = {}) {
  el.piezas.forEach((p, i) => {
    const k = pr(lt, ini + i * paso, dur, E.out5);
    let o = k, y = (1 - k) * dy, b = (1 - k) * blur, s = 1 + (1 - k) * ds;
    if (salida !== null) { const q = pr(lt, salida + i * 0.02, 0.3, E.inn); o *= 1 - q; y -= q * 40; b += q * 10; }
    pon(p, { y, o, b, s });
  });
}

// ---------- fondo: luces que se mueven + grano ----------
const fondo = h(`<div class="capa"></div>`);
const luces = [
  ['#0d7f76', 0.55], ['#1fb3a4', 0.35], ['#e2b155', 0.18], ['#0a4f6a', 0.4],
].map(([c, a]) => { const d = h(`<div class="abs" style="width:${W * 0.9}px;height:${W * 0.9}px;border-radius:50%;background:radial-gradient(circle,${c} 0%,transparent 62%);opacity:${a}"></div>`); fondo.appendChild(d); return d; });
stage.appendChild(fondo);
const tono = h(`<div class="capa" style="background:radial-gradient(70% 60% at 50% 50%,transparent,rgba(2,12,13,.6))"></div>`); stage.appendChild(tono);
const capaEscenas = h(`<div class="capa"></div>`); stage.appendChild(capaEscenas);
const cvs = document.createElement('canvas'); cvs.width = cvs.height = 256;
{ const g = cvs.getContext('2d'); const d = g.createImageData(256, 256); for (let i = 0; i < d.data.length; i += 4) { const v = Math.random() * 255; d.data[i] = d.data[i + 1] = d.data[i + 2] = v; d.data[i + 3] = 255; } g.putImageData(d, 0, 0); }
const grano = h(`<div class="grano" style="background-image:url(${cvs.toDataURL()})"></div>`); stage.appendChild(grano);
stage.appendChild(h(`<div class="vineta"></div>`));
const destello = h(`<div class="destello"></div>`); stage.appendChild(destello);
const rojo = h(`<div class="capa" style="background:radial-gradient(60% 60% at 50% 50%,rgba(255,80,60,.0),rgba(160,20,10,.55));opacity:0;pointer-events:none"></div>`); stage.appendChild(rojo);

function fondoEn(t, calor = 0) {
  luces.forEach((d, i) => {
    const a = t * (0.12 + i * 0.05) + i * 1.7;
    pon(d, { x: W * (0.5 + 0.38 * Math.cos(a)) - W * 0.45, y: H * (0.5 + 0.34 * Math.sin(a * 1.3)) - W * 0.45, s: 1 + 0.15 * Math.sin(a * 0.7), o: 1 });
  });
  grano.style.transform = `translate(${Math.floor(ruido(Math.floor(t * FPS)) * 120)}px,${Math.floor(ruido(Math.floor(t * FPS) + 7) * 120)}px)`;
  rojo.style.opacity = calor;
}

// ---------- escenas ----------
const escenas = [];
const escena = (a, b, crear, actualizar) => { const el = h(`<div class="capa" style="display:none"></div>`); capaEscenas.appendChild(el); const st = crear(el) || {}; escenas.push({ a, b, el, st, actualizar }); };
let golpes = [];      // instantes con sacudida de cámara
let flashes = [];     // [t, intensidad]
let calorEn = () => 0;

// ===================== ANUNCIO =====================
const FUNC = [
  { k: 'Agenda', t: 'Agenda <span class="menta">sin choques</span>', s: 'Cada profesional con su horario. Huecos libres al instante y recordatorios por WhatsApp.', c: 'web-03-agenda', fx: 0.55, fy: 0.25, d: 0.6, v: 1.6, i: 'agenda' },
  { k: 'Odontograma', t: 'Odontograma <span class="menta">digital</span>', s: 'Marca caras y piezas con un toque. Guarda versiones e imprímelo.', c: 'web-05-odontograma', fx: 0.5, fy: 0.45, d: 1.4, v: 2.4, i: 'diente' },
  { k: 'Oportunidades', t: 'Sabe a quién <span class="menta">escribir hoy</span>', s: 'Citas sin confirmar, cumpleaños, saldos y pacientes por recuperar. El mensaje ya está escrito.', c: 'web-06-oportunidades', fx: 0.62, fy: 0.08, d: 1.6, v: 1.6, i: 'chat' },
  { k: 'Cartera', t: 'Quién te debe, <span class="oro">al instante</span>', s: 'Cuánto abonó cada paciente y cuánto le falta. De todos, en una sola pantalla.', c: 'web-07-cartera', fx: 0.62, fy: 0.12, d: 1.8, v: 1.7, i: 'billetera' },
  { k: 'Finanzas', t: 'Finanzas <span class="menta">claras</span>', s: 'Ingresos, gastos fijos, utilidad y proyección de lo que entra y sale.', c: 'web-08-finanzas', fx: 0.6, fy: 0.25, d: 1.8, v: 1.9, i: 'grafico' },
  { k: 'Documentos', t: 'Comprobantes <span class="oro">con tu logo</span>', s: 'Recibos de abono, estados de cuenta y certificados listos para imprimir.', c: 'web-09-comprobante', fx: 0.5, fy: 0.15, d: 1.2, v: 1.8, i: 'recibo' },
  { k: 'Tu marca', t: 'Tu logo. <span class="menta">Tu color.</span>', s: 'La app se viste con la identidad de tu consulta, en la web y en el celular.', c: 'web-10-marca', fx: 0.62, fy: 0.35, d: 5.2, v: 1.5, i: 'paleta' },
  { k: 'App móvil', t: 'Tu consultorio <span class="oro">en el bolsillo</span>', s: 'Agenda, fichas, odontograma y cobros desde el celular.', tel: [['app-04-paciente', 8.2, 1.0], ['app-05-cartera', 3.6, 1.25]], i: 'celular' },
];
const T_FUNC = 7.5, D_FUNC = 3.0;

function anuncio() {
  const DUR = 43;
  golpes = [0.2, 0.7, 1.0, 1.4, 3.0, 3.66, 4.33, 5.0, 37.5];
  flashes = [[5.0, 0.9], [37.5, 0.6], [31.5, 0.25]];
  for (let i = 0; i < 8; i++) flashes.push([T_FUNC + i * D_FUNC, 0.12]);
  calorEn = (t) => cl((t - 2.0) / 0.4) * (1 - cl((t - 4.9) / 0.15)) * 0.8;

  // ---- 1. Gancho ----
  escena(0, 3.0, (el) => {
    const tam = VERT ? 150 : 150;
    const frase = texto(`¿Tu consultorio<br>todavía vive en <span class="oro">papel?</span>`, 'titulo', `left:0;right:0;top:${VERT ? 640 : 310}px;text-align:center;font-size:${tam}px`);
    el.appendChild(frase);
    const caos = [['papel', 'Agenda de papel'], ['tabla', 'Cuentas en Excel'], ['chat', 'Mil chats de WhatsApp'], ['dinero', 'Cobros olvidados']].map(([i, t], k) => {
      const c = h(`<div class="abs tarjeta vidrio" style="display:flex;align-items:center;gap:20px;padding:22px 28px;font-size:${VERT ? 40 : 34}px;font-weight:700">${icono(i, VERT ? 76 : 64, 'linear-gradient(135deg,#ff8a7a,#d64535)')}<span>${t}</span></div>`);
      el.appendChild(c);
      const tach = h(`<div class="tachon" style="left:20px;right:20px;top:48%"></div>`); c.appendChild(tach); c.tach = tach;
      return c;
    });
    return { frase, caos };
  }, (lt, { frase, caos }) => {
    const tiempos = [0.2, 0.2, 0.7, 0.7, 1.0, 1.0, 1.4];
    frase.piezas.forEach((p, i) => {
      const k = pr(lt, tiempos[i] ?? 1.4, 0.32, E.out5);
      const salida = pr(lt, 1.95, 0.35, E.inn);
      pon(p, { s: lerp(1.9, 1, k) * (1 - salida * 0.3), o: k * (1 - salida), b: (1 - k) * 22 + salida * 16, y: -salida * 60 });
    });
    const pos = VERT
      ? [[90, 520, -6], [330, 760, 4], [120, 1020, 5], [300, 1260, -4]]
      : [[150, 220, -6], [1040, 300, 5], [260, 640, 4], [1080, 700, -5]];
    caos.forEach((c, i) => {
      const k = pr(lt, 2.0 + i * 0.09, 0.45, E.back);
      const [x, y, r] = pos[i];
      const fuera = pr(lt, 2.78, 0.22, E.inn);
      pon(c, { x, y: y + (1 - k) * 120 + fuera * 80, r: r * k, s: lerp(0.6, 1, k), o: cl(k * 1.4) * (1 - fuera), b: fuera * 12 });
      c.tach.style.transform = `scaleX(${pr(lt, 2.45 + i * 0.06, 0.18, E.out)})`;
    });
  });

  // ---- 2. El problema en tres golpes ----
  escena(3.0, 5.0, (el) => {
    const lineas = [['Citas que', 'se olvidan.'], ['Cobros que', 'se pierden.'], ['Horas en', 'papeleo.']].map(([a, b], i) => {
      const t = texto(`${a} <span style="color:var(--rojo)">${b}</span>`, 'titulo', `left:0;right:0;text-align:center;font-size:${VERT ? 104 : 120}px;top:${(VERT ? 520 : 300) + i * (VERT ? 300 : 170)}px`);
      el.appendChild(t); return t;
    });
    return { lineas };
  }, (lt, { lineas }) => {
    lineas.forEach((t, i) => {
      const ini = i * 0.66;
      const fuera = pr(lt, 1.75, 0.25, E.inn);
      t.piezas.forEach((p, j) => {
        const k = pr(lt, ini + j * 0.05, 0.3, E.out5);
        const atenuar = i < 2 ? pr(lt, ini + 0.66, 0.2) * 0.55 : 0;
        pon(p, { x: (1 - k) * (i % 2 ? 160 : -160), o: k * (1 - atenuar) * (1 - fuera), b: (1 - k) * 18 + fuera * 20, s: 1 + fuera * 0.2 });
      });
    });
  });

  // ---- 3. Revelación ----
  escena(5.0, 7.6, (el) => {
    const rayos = h(`<div class="abs" style="left:50%;top:${VERT ? 760 : 400}px;width:2400px;height:2400px;margin:-1200px 0 0 -1200px;
      background:repeating-conic-gradient(from 0deg,rgba(94,234,212,.10) 0 6deg,transparent 6deg 18deg);border-radius:50%;
      -webkit-mask:radial-gradient(circle,#000 0,transparent 60%);mask:radial-gradient(circle,#000 0,transparent 60%)"></div>`);
    const halo = h(`<div class="abs" style="left:50%;top:${VERT ? 760 : 400}px;width:900px;height:900px;margin:-450px 0 0 -450px;border-radius:50%;background:radial-gradient(circle,rgba(94,234,212,.55),transparent 60%)"></div>`);
    const logo = h(`<div class="abs" style="left:50%;top:${VERT ? 760 : 400}px;margin:-110px 0 0 -110px">${MARCA(220)}</div>`);
    const nombre = texto(`Sistema <span class="menta">Odontológico</span>`, 'titulo', `left:0;right:0;text-align:center;top:${VERT ? 930 : 560}px;font-size:${VERT ? 120 : 130}px`);
    const lema = texto(`Tu consulta completa. En una sola app.`, 'medio', `left:0;right:0;text-align:center;top:${VERT ? 1180 : 730}px;font-size:${VERT ? 54 : 50}px;color:#cfe7e4`);
    [rayos, halo, logo, nombre, lema].forEach((e) => el.appendChild(e));
    return { rayos, halo, logo, nombre, lema };
  }, (lt, s) => {
    const fuera = pr(lt, 2.25, 0.35, E.inn);
    pon(s.rayos, { r: lt * 14, s: lerp(0.4, 1, pr(lt, 0, 0.8)), o: pr(lt, 0, 0.3) * (1 - fuera) * 0.9 });
    pon(s.halo, { s: lerp(0.3, 1.1, pr(lt, 0, 0.6)) + 0.04 * Math.sin(lt * 5), o: (1 - fuera) });
    const k = pr(lt, 0.05, 0.8, E.spring);
    pon(s.logo, { s: lerp(0.2, 1, k) * (1 + fuera * 0.4), r: (1 - k) * -40, o: cl(lt / 0.15) * (1 - fuera), b: fuera * 20 });
    animarTexto(s.nombre, lt, 0.35, { paso: 0.1, dy: 80, salida: 2.2, ds: 0.2 });
    animarTexto(s.lema, lt, 0.8, { paso: 0.05, dy: 30, salida: 2.25 });
  });

  // ---- 4. Funciones ----
  FUNC.forEach((f, i) => {
    const a = T_FUNC + i * D_FUNC;
    escena(a, a + D_FUNC, (el) => {
      const num = h(`<div class="abs kicker" style="font-size:${VERT ? 30 : 24}px;${VERT ? 'left:90px;top:250px' : 'left:110px;top:300px'};display:flex;align-items:center;gap:16px">${icono(f.i, VERT ? 64 : 56)}<span>${String(i + 1).padStart(2, '0')} · ${f.k}</span></div>`);
      const tit = texto(f.t, 'titulo', VERT ? `left:90px;right:70px;top:360px;font-size:104px` : `left:110px;width:640px;top:390px;font-size:88px`);
      const sub = texto(f.s, '', VERT ? `left:90px;right:90px;top:${f.tel ? 600 : 600}px;font-size:40px;line-height:1.35;color:#b9d3d0` : `left:110px;width:600px;top:${f.t.length > 40 ? 640 : 640}px;font-size:31px;line-height:1.4;color:#b9d3d0`);
      [num, tit, sub].forEach((e) => el.appendChild(e));
      let dispositivos = [];
      if (f.tel) {
        f.tel.forEach(([n, d, v], k) => {
          const c = clip(n); const alto = VERT ? 1000 : 860;
          const t = telefono(c, alto); t.style.left = (VERT ? 90 + k * 470 : 900 + k * 440) + 'px'; t.style.top = (VERT ? 820 : 120) + 'px';
          el.appendChild(t); dispositivos.push({ el: t, c, d, v, k });
        });
      } else {
        const c = clip(f.c); const ancho = VERT ? 980 : 1120;
        const v = ventana(c, ancho, VERT ? { alto: 1000, zoom: 1.85, fx: f.fx ?? 0.62, fy: f.fy ?? 0.3 } : null); v.style.left = (VERT ? 50 : 720) + 'px'; v.style.top = (VERT ? 800 : 190) + 'px';
        el.appendChild(v); dispositivos.push({ el: v, c, d: f.d, v: f.v, k: 0 });
      }
      const prog = h(`<div class="barra-prog" style="${VERT ? 'left:90px;right:90px;top:200px' : 'left:110px;width:600px;top:260px'}"><i></i></div>`);
      el.appendChild(prog);
      return { num, tit, sub, dispositivos, prog };
    }, (lt, s) => {
      const fuera = pr(lt, D_FUNC - 0.32, 0.32, E.inn);
      pon(s.num, { x: (1 - pr(lt, 0, 0.4)) * -40, o: pr(lt, 0, 0.3) * (1 - fuera) });
      animarTexto(s.tit, lt, 0.05, { paso: 0.06, dy: 70, salida: D_FUNC - 0.34 });
      animarTexto(s.sub, lt, 0.35, { paso: 0.015, dy: 24, blur: 8, salida: D_FUNC - 0.3 });
      s.prog.firstElementChild.style.transform = `scaleX(${(i + pr(lt, 0, D_FUNC, E.lin)) / FUNC.length})`;
      pon(s.prog, { o: 1 - fuera });
      s.dispositivos.forEach(({ el, c, d, v, k }) => {
        c.ir(d + lt * v);
        const ent = pr(lt, 0.0 + k * 0.12, 0.7, E.out5);
        const deriva = lt / D_FUNC;
        if (VERT) {
          pon(el, { y: (1 - ent) * 260 + fuera * -140, s: lerp(0.86, 1, ent) * (1 + deriva * 0.03) * (1 - fuera * 0.08), rx: (1 - ent) * 18 + 4 - deriva * 4, o: cl(ent * 1.6) * (1 - fuera), b: (1 - ent) * 10 + fuera * 14 });
        } else {
          pon(el, { x: (1 - ent) * 380 + fuera * 160, s: lerp(0.86, 1, ent) * (1 + deriva * 0.035), ry: -14 + (1 - ent) * -18 + deriva * 6, rx: 3, o: cl(ent * 1.6) * (1 - fuera), b: (1 - ent) * 12 + fuera * 14 });
        }
      });
    });
  });

  // ---- 5. Para quién ----
  escena(31.5, 35.2, (el) => {
    const tit = texto(`Hecho para <span class="menta">cualquier consulta</span>`, 'titulo', `left:0;right:0;text-align:center;top:${VERT ? 300 : 170}px;font-size:${VERT ? 96 : 88}px`);
    const datos = [['persona', 'Trabajas solo', 'Agenda, fichas y cobros sin complicarte.'], ['equipo', 'Consultorio pequeño', 'Dos o tres odontólogos, cada uno con su agenda.'], ['clinica', 'Clínica con equipo', 'Recepción, caja, inventario y laboratorio.']];
    const tarjetas = datos.map(([i, t, d], k) => {
      const c = h(`<div class="abs tarjeta vidrio" style="${VERT ? `left:110px;right:110px;top:${640 + k * 300}px;display:flex;gap:34px;align-items:center;padding:40px` : `left:${150 + k * 560}px;top:420px;width:500px;height:360px;padding:40px`}">
        ${icono(i, VERT ? 110 : 96)}<div style="${VERT ? '' : 'margin-top:30px'}"><div class="medio" style="font-size:${VERT ? 52 : 44}px">${t}</div><div style="font-size:${VERT ? 32 : 26}px;color:#b9d3d0;margin-top:12px;line-height:1.35">${d}</div></div></div>`);
      el.appendChild(c); return c;
    });
    const pie = texto(`Activa solo lo que necesitas. <span class="oro">Crece cuando quieras.</span>`, 'medio', `left:0;right:0;text-align:center;top:${VERT ? 1600 : 870}px;font-size:${VERT ? 46 : 44}px`);
    el.appendChild(tit); el.appendChild(pie);
    return { tit, tarjetas, pie };
  }, (lt, s) => {
    const fuera = pr(lt, 3.35, 0.35, E.inn);
    animarTexto(s.tit, lt, 0.05, { paso: 0.07, salida: 3.35 });
    s.tarjetas.forEach((c, k) => { const e = pr(lt, 0.45 + k * 0.22, 0.7, E.spring); pon(c, { y: (1 - e) * 140 - fuera * 60, s: lerp(0.8, 1, e), o: cl(e * 1.5) * (1 - fuera), b: fuera * 12 }); });
    animarTexto(s.pie, lt, 1.5, { paso: 0.05, dy: 30, salida: 3.35 });
  });

  // ---- 6. Confianza ----
  escena(35.2, 37.6, (el) => {
    const datos = [['escudo', 'Datos protegidos', 'Cumple la LOPDP'], ['nube', 'Respaldo diario', 'Automático'], ['dispositivos', 'Web y app móvil', 'Los mismos datos'], ['reloj', 'Listo en minutos', 'Sin instalar nada']];
    const items = datos.map(([i, t, d], k) => {
      const c = h(`<div class="abs tarjeta vidrio" style="display:flex;align-items:center;gap:24px;padding:28px 34px;${VERT ? `left:110px;right:110px;top:${520 + k * 230}px` : `left:${k % 2 ? 990 : 250}px;top:${k < 2 ? 300 : 560}px;width:680px`}">
        ${icono(i, 84)}<div><div class="medio" style="font-size:${VERT ? 48 : 42}px">${t}</div><div style="font-size:${VERT ? 30 : 26}px;color:#9fd8cf;margin-top:6px">${d}</div></div></div>`);
      el.appendChild(c); return c;
    });
    return { items };
  }, (lt, s) => {
    const fuera = pr(lt, 2.1, 0.3, E.inn);
    s.items.forEach((c, k) => { const e = pr(lt, 0.05 + k * 0.12, 0.55, E.out5); pon(c, { x: (1 - e) * (k % 2 ? 120 : -120), o: e * (1 - fuera), b: (1 - e) * 10 + fuera * 10, s: 1 - fuera * 0.05 }); });
  });

  // ---- 7. Llamado a la acción ----
  escena(37.6, DUR, (el) => {
    const logo = h(`<div class="abs" style="left:50%;top:${VERT ? 380 : 150}px;margin-left:-60px">${MARCA(120)}</div>`);
    const tit = texto(`Agenda tu <span class="oro">demo gratis</span>`, 'titulo', `left:0;right:0;text-align:center;top:${VERT ? 600 : 330}px;font-size:${VERT ? 128 : 140}px`);
    const sub = texto(`Te lo mostramos con tus datos, en 15 minutos.`, 'medio', `left:0;right:0;text-align:center;top:${VERT ? 900 : 520}px;font-size:${VERT ? 46 : 44}px;color:#cfe7e4`);
    const boton = h(`<div class="abs boton" style="left:50%;top:${VERT ? 1080 : 650}px;padding:${VERT ? '34px 56px' : '30px 54px'};font-size:${VERT ? 48 : 46}px;white-space:nowrap">${svg('chat', VERT ? 50 : 46, '#04191b')}<span>${CONTACTO}</span>${svg('flecha', VERT ? 46 : 42, '#04191b')}</div>`);
    const pie = texto(`Odontólogos independientes · Consultorios · Clínicas`, '', `left:0;right:0;text-align:center;top:${VERT ? 1330 : 860}px;font-size:${VERT ? 32 : 28}px;letter-spacing:.06em;color:#9fd8cf`);
    [logo, tit, sub, boton, pie].forEach((e) => el.appendChild(e));
    return { logo, tit, sub, boton, pie };
  }, (lt, s) => {
    const fin = pr(lt, DUR - 37.6 - 0.9, 0.9, E.io);
    pon(s.logo, { s: lerp(0.3, 1, pr(lt, 0, 0.7, E.spring)), o: pr(lt, 0, 0.2) * (1 - fin) });
    animarTexto(s.tit, lt, 0.1, { paso: 0.09, dy: 90, ds: 0.3 });
    animarTexto(s.sub, lt, 0.6, { paso: 0.035, dy: 30 });
    const e = pr(lt, 1.0, 0.7, E.spring);
    const ancho = s.boton.offsetWidth;
    const latido = 1 + 0.035 * Math.max(0, Math.sin((lt - 1.6) * Math.PI * 2 / 1.0)) * cl(lt - 1.6);
    pon(s.boton, { x: -ancho / 2, s: lerp(0.5, 1, e) * latido, o: cl(e * 1.5) });
    s.boton.style.boxShadow = `0 30px ${80 + 40 * (latido - 1) * 28}px -20px rgba(226,177,85,${0.55 + (latido - 1) * 8}),inset 0 2px 0 rgba(255,255,255,.6)`;
    animarTexto(s.pie, lt, 1.6, { paso: 0.03, dy: 20 });
    stage.style.filter = fin > 0 ? `brightness(${1 - fin})` : 'none';
  });
  return DUR;
}

// ===================== AVANCE «PRÓXIMAMENTE» =====================
function teaser() {
  const DUR = 20;
  golpes = [2.0, 12.0, 16.0];
  flashes = [[2.0, 0.8], [12.0, 0.7], [16.0, 0.9]];
  calorEn = () => 0;
  // 1. Algo llega
  escena(0, 2.0, (el) => {
    const t1 = texto(`Algo nuevo llega`, 'titulo', `left:0;right:0;text-align:center;top:${VERT ? 760 : 380}px;font-size:${VERT ? 120 : 130}px`);
    const t2 = texto(`a tu <span class="menta">consultorio</span>`, 'titulo', `left:0;right:0;text-align:center;top:${VERT ? 900 : 530}px;font-size:${VERT ? 120 : 130}px`);
    el.appendChild(t1); el.appendChild(t2); return { t1, t2 };
  }, (lt, s) => {
    animarTexto(s.t1, lt, 0.15, { paso: 0.12, dy: 0, blur: 30, ds: 0.4, dur: 0.6 });
    animarTexto(s.t2, lt, 0.8, { paso: 0.12, dy: 0, blur: 30, ds: 0.4, dur: 0.6 });
    const f = pr(lt, 1.75, 0.25, E.inn);
    pon(s.t1, { s: 1 + f * 0.6, o: 1 - f, b: f * 20 }); pon(s.t2, { s: 1 + f * 0.6, o: 1 - f, b: f * 20 });
  });
  // 2. Ráfaga de tomas al ritmo (cada 0,5 s), con una palabra cada segundo.
  const cortes = [
    ['web-02-panel', 1.0, 'Tu día'], ['web-03-agenda', 3.0, null], ['web-05-odontograma', 5.0, 'Odontograma'], ['app-04-paciente', 9.5, null],
    ['web-06-oportunidades', 3.5, 'WhatsApp'], ['web-07-cartera', 3.0, null], ['web-08-finanzas', 4.5, 'Finanzas'], ['app-05-cartera', 4.0, null],
    ['web-09-comprobante', 2.5, 'Tu logo'], ['web-10-marca', 6.0, null], ['web-10-marca', 8.0, 'Tu color'], ['app-03-agenda', 2.0, null],
    ['web-12-modo-oscuro', 3.2, 'Modo oscuro'], ['web-11-legal', 1.5, null], ['app-02-panel', 1.5, 'En tu celular'], ['app-07-oportunidades', 3.0, null],
    ['web-04-paciente', 3.0, 'Todo'], ['web-13-busqueda', 2.5, null], ['web-10-marca', 9.5, 'Listo'], ['web-02-panel', 3.0, null],
  ];
  cortes.forEach(([n, d, palabra], i) => {
    const a = 2.0 + i * 0.5;
    escena(a, a + 0.5, (el) => {
      const c = clip(n); const movil = n.startsWith('app');
      let disp;
      if (movil) { disp = telefono(c, VERT ? 1500 : 900); disp.style.left = (W - (VERT ? 1500 : 900) * 0.4618) / 2 + 'px'; disp.style.top = (H - (VERT ? 1500 : 900)) / 2 + 'px'; }
      else { const anc = VERT ? 1000 : 1500; disp = ventana(c, anc, VERT ? { alto: 1150, zoom: 2.1, fx: 0.6, fy: 0.3 } : null); disp.style.left = (W - anc) / 2 + 'px'; disp.style.top = (VERT ? 300 : 120) + 'px'; }
      el.appendChild(disp);
      let pal = null;
      if (palabra) { pal = texto(palabra, 'titulo', `left:0;right:0;text-align:center;top:${VERT ? 1560 : 860}px;font-size:${VERT ? 120 : 110}px;text-shadow:0 20px 60px rgba(0,0,0,.6)`); el.appendChild(pal); }
      return { c, disp, d, pal, movil };
    }, (lt, s) => {
      s.c.ir(s.d + lt * 1.4);
      const e = pr(lt, 0, 0.18, E.out5);
      const dir = i % 2 ? 1 : -1;
      pon(s.disp, { x: (1 - e) * 220 * dir, s: lerp(1.15, 1, e) * (1 + lt * 0.08), r: (1 - e) * 3 * dir, b: (1 - e) * 16, o: 1, ry: s.movil ? 0 : dir * 6, rx: s.movil ? 0 : 4 });
      if (s.pal) s.pal.piezas.forEach((p) => { const k = pr(lt, 0.02, 0.2, E.out5); pon(p, { s: lerp(1.6, 1, k), o: k, b: (1 - k) * 18 }); });
    });
  });
  // 3. Pausa y logo desenfocado
  escena(12.0, 16.0, (el) => {
    const logo = h(`<div class="abs" style="left:50%;top:${VERT ? 700 : 330}px;margin-left:-110px">${MARCA(220)}</div>`);
    const nombre = texto(`Sistema <span class="menta">Odontológico</span>`, 'titulo', `left:0;right:0;text-align:center;top:${VERT ? 980 : 600}px;font-size:${VERT ? 116 : 120}px`);
    const lema = texto(`Para odontólogos independientes, consultorios y clínicas.`, 'medio', `left:${VERT ? 80 : 0}px;right:${VERT ? 80 : 0}px;text-align:center;top:${VERT ? 1240 : 770}px;font-size:${VERT ? 46 : 40}px;color:#cfe7e4`);
    [logo, nombre, lema].forEach((e) => el.appendChild(e));
    return { logo, nombre, lema };
  }, (lt, s) => {
    const enfoque = pr(lt, 0, 2.6, E.io);
    const f = pr(lt, 3.7, 0.3, E.inn);
    pon(s.logo, { s: lerp(1.6, 1, enfoque), b: (1 - enfoque) * 40 + f * 20, o: cl(lt / 0.4) * (1 - f) });
    animarTexto(s.nombre, lt, 1.2, { paso: 0.12, dy: 40, blur: 20, salida: 3.7 });
    animarTexto(s.lema, lt, 2.0, { paso: 0.04, dy: 24, salida: 3.7 });
  });
  // 4. PRÓXIMAMENTE
  escena(16.0, DUR, (el) => {
    const t = h(`<div class="abs titulo" style="left:0;right:0;text-align:center;top:${VERT ? 740 : 330}px;white-space:nowrap;font-size:${VERT ? 112 : 190}px">${'PRÓXIMAMENTE'.split('').map((c) => `<span class="palabra">${c}</span>`).join('')}</div>`);
    t.piezas = [...t.querySelectorAll('.palabra')];
    const linea = h(`<div class="abs" style="left:50%;top:${VERT ? 900 : 560}px;width:${VERT ? 700 : 900}px;margin-left:-${VERT ? 350 : 450}px;height:4px;border-radius:4px;background:linear-gradient(90deg,transparent,var(--oro),transparent)"></div>`);
    const cta = h(`<div class="abs boton" style="left:50%;top:${VERT ? 1000 : 640}px;padding:26px 48px;font-size:${VERT ? 42 : 40}px;white-space:nowrap">${svg('chat', 42, '#04191b')}<span>Reserva tu demo: ${CONTACTO}</span></div>`);
    [t, linea, cta].forEach((e) => el.appendChild(e));
    return { t, linea, cta };
  }, (lt, s) => {
    const n = s.t.piezas.length;
    s.t.piezas.forEach((p, i) => {
      const k = pr(lt, Math.abs(i - (n - 1) / 2) * 0.05, 0.7, E.out5);
      pon(p, { y: (1 - k) * 50, o: k, b: (1 - k) * 20, s: lerp(1.4, 1, k) });
    });
    s.t.style.letterSpacing = `${lerp(VERT ? 0.12 : 0.25, VERT ? 0.01 : 0.04, pr(lt, 0, 3.5, E.out))}em`;
    pon(s.linea, { sx: pr(lt, 0.4, 0.8, E.out5), o: 1 });
    const e = pr(lt, 1.1, 0.7, E.spring);
    pon(s.cta, { x: -s.cta.offsetWidth / 2, s: lerp(0.6, 1, e), o: cl(e * 1.5) });
    const fin = pr(lt, DUR - 16 - 0.8, 0.8, E.io);
    stage.style.filter = fin > 0 ? `brightness(${1 - fin})` : 'none';
  });
  return DUR;
}

const DURACION = V === 'teaser' ? teaser() : anuncio();

window.FILM = {
  dur: DURACION, W, H, fps: FPS,
  async render(t) {
    pendientes.length = 0;
    stage.style.filter = 'none';
    fondoEn(t, calorEn(t));
    // Sacudida de cámara en cada golpe.
    let sx = 0, sy = 0;
    for (const g of golpes) { const d = t - g; if (d >= 0 && d < 0.35) { const a = 14 * Math.exp(-d * 12); sx += Math.sin(d * 90) * a; sy += Math.cos(d * 77) * a; } }
    capaEscenas.style.transform = `translate(${sx}px,${sy}px)`;
    let fl = 0; for (const [ft, i] of flashes) { const d = t - ft; if (d >= 0 && d < 0.6) fl = Math.max(fl, i * Math.exp(-d * 9)); }
    destello.style.opacity = fl;
    for (const e of escenas) {
      const vis = t >= e.a && t < e.b;
      e.el.style.display = vis ? 'block' : 'none';
      if (vis) e.actualizar(t - e.a, e.st);
    }
    await Promise.all(pendientes);
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  },
};
