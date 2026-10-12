// Montaje animado cuadro a cuadro. Estilo de anuncio para redes: bloques de
// color sólido que cambian al ritmo, tipografía grande con resaltador, y las
// pantallas reales COMPLETAS (laptop + celular), nunca recortadas.
// FILM.render(t) deja el escenario en el instante t (segundos).
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

const C = { tinta: '#0f1a1c', papel: '#f4f3ef', verde: '#0d7f76', menta: '#d9efeb', amarillo: '#ffd23f', coral: '#ff5a4e', blanco: '#ffffff' };
const OSCUROS = new Set(['tinta', 'verde', 'coral']);

// ---------- utilidades ----------
const cl = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, k) => a + (b - a) * k;
const E = {
  lin: (t) => t,
  out: (t) => 1 - Math.pow(1 - t, 3),
  out5: (t) => 1 - Math.pow(1 - t, 5),
  inn: (t) => t * t * t,
  io: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  firme: (t) => (t >= 1 ? 1 : 1 - (1 + 8 * t) * Math.exp(-8 * t)),          // llega firme
  rebote: (t) => (t >= 1 ? 1 : 1 - Math.exp(-7 * t) * Math.cos(10 * t)),     // con un pequeño rebote
};
const pr = (lt, s, d, e = E.out) => e(cl((lt - s) / d));
const h = (html) => { const d = document.createElement('div'); d.innerHTML = html.trim(); return d.firstElementChild; };
function pon(el, o = {}) {
  const { x = 0, y = 0, s = 1, sx, sy, r = 0, o: op = 1 } = o;
  el.style.transform = `translate3d(${x}px,${y}px,0) rotate(${r}deg) scale(${sx ?? s},${sy ?? s})`;
  el.style.opacity = op;
}

// ---------- íconos (Material) ----------
const IC = {
  agenda: 'M17 12h-5v5h5v-5zM16 1v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2h-1V1h-2zm3 18H5V8h14v11z',
  chat: 'M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 9h12v2H6V9zm8 5H6v-2h8v2zm4-6H6V6h12v2z',
  billetera: 'M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8zm4-2.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z',
  grafico: 'M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z',
  recibo: 'M18 17H6v-2h12v2zm0-4H6v-2h12v2zm0-4H6V7h12v2zM3 22l1.5-1.5L6 22l1.5-1.5L9 22l1.5-1.5L12 22l1.5-1.5L15 22l1.5-1.5L18 22l1.5-1.5L21 22V2l-1.5 1.5L18 2l-1.5 1.5L15 2l-1.5 1.5L12 2l-1.5 1.5L9 2 7.5 3.5 6 2 4.5 3.5 3 2v20z',
  paleta: 'M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9c.83 0 1.5-.67 1.5-1.5 0-.39-.15-.74-.39-1.01-.23-.26-.38-.61-.38-.99 0-.83.67-1.5 1.5-1.5H16c2.76 0 5-2.24 5-5 0-4.42-4.03-8-9-8zm-5.5 9c-.83 0-1.5-.67-1.5-1.5S5.67 9 6.5 9 8 9.67 8 10.5 7.33 12 6.5 12zm3-4C8.67 8 8 7.33 8 6.5S8.67 5 9.5 5s1.5.67 1.5 1.5S10.33 8 9.5 8zm5 0c-.83 0-1.5-.67-1.5-1.5S13.67 5 14.5 5s1.5.67 1.5 1.5S15.33 8 14.5 8zm3 4c-.83 0-1.5-.67-1.5-1.5S16.67 9 17.5 9s1.5.67 1.5 1.5-.67 1.5-1.5 1.5z',
  flecha: 'M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z',
  ok: 'M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z',
  persona: 'M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z',
  equipo: 'M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z',
  clinica: 'M19 3H5c-1.1 0-1.99.9-1.99 2L3 19c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-1 11h-4v4h-4v-4H6v-4h4V6h4v4h4v4z',
  escudo: 'M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z',
  nube: 'M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM10 17l-3.5-3.5 1.41-1.41L10 14.17 15.18 9l1.41 1.41L10 17z',
  dispositivos: 'M4 6h18V4H4c-1.1 0-2 .9-2 2v11H0v3h14v-3H4V6zm19 2h-6c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h6c.55 0 1-.45 1-1V9c0-.55-.45-1-1-1zm-1 9h-4v-7h4v7z',
  reloj: 'M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z',
  diente: 'M12 2.6c-4.6 0-7.9 2.5-7.9 6.7 0 2.9.8 5.2 1.4 8.2.5 2.2.8 4.3 2.3 4.3s1.8-2 2.3-4.1c.4-1.5 1-2.3 1.9-2.3s1.5.8 1.9 2.3c.5 2.1.8 4.1 2.3 4.1s1.8-2.1 2.3-4.3c.6-3 1.4-5.3 1.4-8.2 0-4.2-3.3-6.7-7.9-6.7z',
};
const svg = (n, t, color = '#fff') => `<svg viewBox="0 0 24 24" width="${t}" height="${t}" style="fill:${color};flex-shrink:0;display:block"><path d="${IC[n]}"/></svg>`;
const icono = (n, t, fondo, color = '#fff') => `<span class="icono" style="width:${t}px;height:${t}px;border-radius:${Math.round(t * 0.28)}px;background:${fondo}">${svg(n, Math.round(t * 0.54), color)}</span>`;
const MARCA = (t, fondo, tinta) => `<span class="icono" style="width:${t}px;height:${t}px;border-radius:${Math.round(t * 0.28)}px;background:${fondo}">
  <svg viewBox="0 0 24 24" width="${Math.round(t * 0.6)}" height="${Math.round(t * 0.6)}"><path fill="${tinta}" d="${IC.diente}"/><path d="M8.6 9.6q3.4 2.8 6.8 0" stroke="${fondo}" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg></span>`;

// ---------- clips (secuencias de cuadros) ----------
const pendientes = [];
class Clip {
  constructor(nombre, total) { this.nombre = nombre; this.total = total; this.imgs = []; this.n = 0; }
  imagen() { const i = document.createElement('img'); this.imgs.push(i); return i; }
  ir(seg) {
    const n = cl(Math.floor(seg * FPS) + 1, 1, this.total);
    if (n !== this.n) {
      this.n = n;
      const src = `cuadros/${this.nombre}/${String(n).padStart(5, '0')}.jpg`;
      for (const i of this.imgs) { i.src = src; pendientes.push(i.decode().catch(() => {})); }
    }
  }
}
const TOTALES = window.TOTALES || {};
const clip = (n) => new Clip(n, TOTALES[n] || 300);

// Laptop con la pantalla COMPLETA (16:9).
function laptop(c, anchoPantalla) {
  const el = h(`<div class="abs laptop" style="width:${anchoPantalla + 32}px"><div class="tapa" style="position:relative"><span class="camara"></span><div class="pantalla" style="height:${Math.round(anchoPantalla * 9 / 16)}px"></div></div><div class="base"></div></div>`);
  el.querySelector('.pantalla').appendChild(c.imagen());
  el.alto = Math.round(anchoPantalla * 9 / 16) + 34 + 18;
  return el;
}
function telefono(c, alto) {
  const ancho = Math.round(alto * 0.4618);
  const el = h(`<div class="abs telefono" style="width:${ancho}px;height:${alto}px"><div class="pantalla"><div class="isla"></div></div></div>`);
  el.firstElementChild.appendChild(c.imagen());
  el.ancho = ancho;
  return el;
}
// Lupa: zona ampliada de la misma pantalla (la laptop sigue completa al lado).
function lupa(c, ancho, alto, { z, fx, fy }) {
  const el = h(`<div class="abs lupa" style="width:${ancho}px;height:${alto}px"><div class="marco"></div></div>`);
  const i = c.imagen(); const ai = (ancho - 10) * z, hi = ai * 9 / 16;
  i.style.cssText = `position:absolute;max-width:none;width:${ai}px;height:${hi}px;left:${-(ai - ancho + 10) * fx}px;top:${-(hi - alto + 10) * fy}px`;
  el.firstElementChild.appendChild(i);
  return el;
}

// Texto palabra por palabra. <m>…</m> marca la frase con el resaltador.
function texto(html, clase, estilo, { marca = C.amarillo, tintaMarca = C.tinta } = {}) {
  const el = h(`<div class="abs ${clase}" style="${estilo}"></div>`);
  const tmp = document.createElement('div'); tmp.innerHTML = html;
  const piezas = []; const marcas = [];
  const recorrer = (nodo, destino) => {
    for (const n of [...nodo.childNodes]) {
      if (n.nodeType === 3) {
        n.textContent.split(/(\s+)/).forEach((p) => {
          if (!p) return;
          if (/^\s+$/.test(p)) { destino.appendChild(document.createTextNode(' ')); return; }
          const s = document.createElement('span'); s.className = 'palabra'; s.textContent = p; destino.appendChild(s); piezas.push(s);
        });
      } else if (n.nodeName === 'BR') destino.appendChild(document.createElement('br'));
      else if (n.nodeName === 'M') {
        const m = h(`<span class="marca"><span class="fondo-marca" style="background:${marca}"></span><span class="marca-in" style="color:${tintaMarca}"></span></span>`);
        destino.appendChild(m); marcas.push(m.firstElementChild); recorrer(n, m.lastElementChild);
      } else { const c2 = n.cloneNode(false); destino.appendChild(c2); recorrer(n, c2); }
    }
  };
  recorrer(tmp, el);
  el.piezas = piezas; el.marcas = marcas;
  return el;
}
function animarTexto(el, lt, ini, { paso = 0.05, dur = 0.45, dy = 50, marcaEn = null, golpe = false } = {}) {
  el.piezas.forEach((p, i) => {
    const k = pr(lt, ini + i * paso, golpe ? 0.14 : dur, E.out5);
    pon(p, golpe ? { s: lerp(1.25, 1, k), o: k } : { y: (1 - k) * dy, o: k });
  });
  const mi = marcaEn ?? ini + el.piezas.length * paso + 0.1;
  el.marcas.forEach((m) => { m.style.transform = `scaleX(${pr(lt, mi, 0.3, E.out5)})`; });
}

// ---------- escenario ----------
const capaEscenas = h(`<div class="capa"></div>`); stage.appendChild(capaEscenas);
const negro = h(`<div class="capa" style="background:#000;opacity:0;pointer-events:none"></div>`); stage.appendChild(negro);
const escenas = [];
// Cada escena tiene su fondo de color. Con `barrido`, entra 0,3 s antes
// cubriendo la anterior con un barrido de su color (a izquierda o derecha).
function escena(a, b, fondo, crear, actualizar, barrido = null) {
  const el = h(`<div class="capa" style="display:none;color:${OSCUROS.has(fondo) ? '#fff' : C.tinta}"></div>`);
  const bg = h(`<div class="capa" style="background:${C[fondo]}"></div>`); el.appendChild(bg);
  capaEscenas.appendChild(el);
  const st = crear(el, OSCUROS.has(fondo)) || {};
  escenas.push({ a: barrido ? a - 0.3 : a, ini: a, b, el, bg, st, actualizar, barrido });
}
let fundidoFinal = 999;

// ===================== ANUNCIO (40 s) =====================
const FUNC = [
  { n: '01', k: 'Agenda', t: 'Agenda<br><m>sin choques</m>', s: 'Cada profesional con su horario. Huecos libres al instante.', i: 'agenda', bg: 'papel',
    chips: ['Día y semana', 'Recordatorios', 'Huecos libres'], web: ['web-03-agenda', 0.6, 1.6], movil: ['app-03-agenda', 1.4, 1.2] },
  { n: '02', k: 'Odontograma', t: 'Odontograma<br><m>digital</m>', s: 'Marca caras y piezas con un toque y guarda cada versión.', i: 'diente', bg: 'verde',
    chips: ['Caras y piezas', 'Versiones', 'Imprimible'], web: ['web-05-odontograma', 1.4, 2.4], movil: ['app-04-paciente', 10.2, 1.0] },
  { n: '03', k: 'Oportunidades', t: 'A quién<br><m>escribir hoy</m>', s: 'Citas sin confirmar, cumpleaños y saldos, con el mensaje listo.', i: 'chat', bg: 'tinta',
    chips: ['Por confirmar', 'Cumpleaños', 'Saldos'], web: ['web-06-oportunidades', 1.6, 1.6], movil: ['app-07-oportunidades', 4.2, 1.2] },
  { n: '04', k: 'Cartera', t: 'Quién te debe,<br><m>al instante</m>', s: 'Cuánto abonó cada paciente y cuánto le falta.', i: 'billetera', bg: 'menta',
    chips: ['Abonos', 'Saldos', 'Tratamientos'], web: ['web-07-cartera', 1.8, 1.7], movil: ['app-05-cartera', 4.0, 1.2] },
  { n: '05', k: 'Finanzas', t: 'Tus números,<br><m>claros</m>', s: 'Ingresos, gastos fijos, utilidad y proyección de caja.', i: 'grafico', bg: 'papel',
    chips: ['Gastos fijos', 'Utilidad', 'Proyección'], web: ['web-08-finanzas', 1.8, 1.9], movil: ['app-06-finanzas', 4.4, 1.1] },
  { n: '06', k: 'Documentos', t: 'Comprobantes<br><m>con tu logo</m>', s: 'Recibos, estados de cuenta y certificados listos para imprimir.', i: 'recibo', bg: 'tinta',
    web: ['web-09-comprobante', 1.2, 1.8], lupa: { z: 2.3, fx: 0.62, fy: 0.03 } },
  { n: '07', k: 'Tu marca', t: 'Tu logo.<br><m>Tu color.</m>', s: 'La app se viste con la identidad de tu consulta.', i: 'paleta', bg: 'verde',
    web: ['web-10-marca', 5.2, 1.5], lupa: { z: 3.0, fx: 0.4, fy: 0.62 } },
  { n: '08', k: 'Legal', t: 'Todo en regla,<br><m>sin papeleo</m>', s: 'Protección de datos, respaldos diarios y acceso seguro.', i: 'escudo', bg: 'papel',
    web: ['web-11-legal', 0.6, 1.3], lupa: { z: 2.6, fx: 0.2, fy: 0.45 } },
];
const T_FUNC = 6.0, D_FUNC = 3.0;

function anuncio() {
  const DUR = 40;
  fundidoFinal = DUR - 0.9;

  // ---- 1. Gancho: preguntas que golpean con el ritmo ----
  const pares = [['¿Agenda', 'en papel?', 'tinta'], ['¿Cobros', 'olvidados?', 'coral'], ['¿Pacientes', 'que no vuelven?', 'tinta']];
  pares.forEach(([a, b, bg], k) => {
    escena(k, k + 1, bg, (el) => {
      const t = texto(`${a}<br><m>${b}</m>`, 'titulo', `left:50px;right:50px;text-align:center;top:${VERT ? 700 : 300}px;font-size:${VERT ? 140 : 180}px`);
      el.appendChild(t); return { t };
    }, (lt, { t }) => {
      t.piezas.forEach((p, i) => { const ini = i === 0 ? 0 : 0.5; const kk = pr(lt, ini, 0.14, E.out5); pon(p, { s: lerp(1.3, 1, kk), o: kk }); });
      t.marcas.forEach((m) => { m.style.transform = `scaleX(${pr(lt, 0.5, 0.18, E.out5)})`; });
    });
  });
  escena(3, 4, 'amarillo', (el) => {
    const t = texto(`Hay una forma<br>mejor.`, 'titulo', `left:50px;right:50px;text-align:center;top:${VERT ? 720 : 320}px;font-size:${VERT ? 150 : 190}px`);
    el.appendChild(t); return { t };
  }, (lt, { t }) => {
    t.piezas.forEach((p, i) => { const ini = [0, 0.15, 0.3, 0.5][i] ?? 0.5; const kk = pr(lt, ini, 0.16, E.out5); pon(p, { s: lerp(1.3, 1, kk), o: kk }); });
  });

  // ---- 2. Revelación (drop) ----
  escena(4, 6, 'verde', (el) => {
    const cy = VERT ? 640 : 250;
    const anillo = h(`<div class="abs" style="left:50%;top:${cy + 100}px;width:200px;height:200px;margin:-100px 0 0 -100px;border-radius:50%;border:6px solid ${C.amarillo}"></div>`);
    const logo = h(`<div class="abs" style="left:50%;top:${cy}px;margin-left:-100px">${MARCA(200, '#fff', C.verde)}</div>`);
    const nombre = texto(`Sistema Odontológico`, 'titulo', `left:30px;right:30px;text-align:center;top:${cy + 260}px;font-size:${VERT ? 104 : 130}px`);
    const lema = texto(`Tu consultorio completo, <m>en una sola app.</m>`, 'medio', `left:60px;right:60px;text-align:center;top:${cy + (VERT ? 520 : 420)}px;font-size:${VERT ? 52 : 50}px`);
    [anillo, logo, nombre, lema].forEach((e) => el.appendChild(e));
    return { anillo, logo, nombre, lema };
  }, (lt, s) => {
    const a = pr(lt, 0, 0.7, E.out5);
    pon(s.anillo, { s: lerp(0.5, 4.5, a), o: 1 - a });
    pon(s.logo, { s: lerp(0.3, 1, pr(lt, 0, 0.5, E.rebote)), o: pr(lt, 0, 0.1) });
    animarTexto(s.nombre, lt, 0.3, { paso: 0.1, dy: 60 });
    animarTexto(s.lema, lt, 0.7, { paso: 0.05, dy: 30, marcaEn: 1.1 });
  });

  // ---- 3. Funciones: bloques de color, laptop completa + celular o lupa ----
  FUNC.forEach((f, i) => {
    const a = T_FUNC + i * D_FUNC;
    escena(a, a + D_FUNC, f.bg, (el, oscuro) => {
      const acento = oscuro ? C.amarillo : C.verde;
      const kick = h(`<div class="abs etiqueta" style="display:flex;align-items:center;gap:16px;font-size:${VERT ? 26 : 22}px;color:${acento};${VERT ? 'left:70px;top:150px' : 'left:110px;top:250px'}">${icono(f.i, VERT ? 54 : 46, acento, oscuro ? C.tinta : '#fff')}<span>${f.n} · ${f.k}</span></div>`);
      const tit = texto(f.t, 'titulo', VERT ? `left:70px;right:40px;top:230px;font-size:108px` : `left:110px;width:600px;top:320px;font-size:80px`);
      const sub = texto(f.s, 'cuerpo', VERT ? `left:70px;right:70px;top:470px;font-size:38px;opacity:.85` : `left:110px;width:540px;top:540px;font-size:30px;opacity:.85`);
      [kick, tit, sub].forEach((e) => el.appendChild(e));
      const c = clip(f.web[0]);
      const lap = VERT ? laptop(c, 920) : laptop(c, f.lupa ? 1000 : 860);
      if (VERT) { lap.style.left = (W - 952) / 2 + 'px'; lap.style.top = '620px'; }
      else if (f.lupa) { lap.style.left = '790px'; lap.style.top = '240px'; }
      else { lap.style.left = '700px'; lap.style.top = '262px'; }
      el.appendChild(lap);
      const disp = [{ el: lap, c, d: f.web[1], v: f.web[2], k: 0, dy: 90 }];
      let extra = null;
      if (f.movil) {
        const cm = clip(f.movil[0]);
        const tel = telefono(cm, VERT ? 600 : 560);
        tel.style.left = (VERT ? W - 70 - tel.ancho : 1636) + 'px'; tel.style.top = (VERT ? 1215 : 250) + 'px';
        el.appendChild(tel); disp.push({ el: tel, c: cm, d: f.movil[1], v: f.movil[2], k: 1, dy: 160 });
      } else {
        extra = lupa(c, VERT ? 470 : 540, VERT ? 330 : 300, f.lupa);
        extra.style.left = (VERT ? W - 70 - 470 : 110) + 'px'; extra.style.top = (VERT ? 1250 : 660) + 'px';
        el.appendChild(extra);
      }
      const chips = (f.chips || []).map((txt, k) => {
        const ch = h(`<div class="abs chip" style="padding:${VERT ? '16px 26px' : '12px 22px'};font-size:${VERT ? 30 : 22}px;background:${oscuro ? 'rgba(255,255,255,.12)' : '#fff'};${VERT ? `left:70px;top:${1260 + k * 100}px` : `left:${110}px;top:${690 + k * 64}px`}">${svg('ok', VERT ? 30 : 22, acento)}${txt}</div>`);
        if (oscuro) ch.style.background = C.tinta === C[f.bg] ? '#1f2c2e' : '#0a6b63';
        el.appendChild(ch); return ch;
      });
      return { kick, tit, sub, disp, extra, chips };
    }, (lt, s) => {
      pon(s.kick, { x: (1 - pr(lt, 0, 0.35)) * -30, o: pr(lt, 0, 0.3) });
      animarTexto(s.tit, lt, 0.05, { paso: 0.06, dy: 70 });
      animarTexto(s.sub, lt, 0.4, { paso: 0.012, dy: 20 });
      s.disp.forEach(({ el, c, d, v, k, dy }) => {
        c.ir(d + Math.max(0, lt) * v);
        const e = pr(lt, 0.05 + k * 0.15, 0.6, E.out5);
        const empuje = 1 + 0.02 * pr(lt, 0.6, 2.4, E.lin);
        pon(el, { y: (1 - e) * dy, s: lerp(0.94, 1, e) * empuje, o: cl(e * 2) });
      });
      if (s.extra) { const e = pr(lt, 0.8, 0.5, E.rebote); pon(s.extra, { s: lerp(0.5, 1, e), o: cl(e * 2), r: (1 - e) * -4 }); }
      s.chips.forEach((ch, k) => { const e = pr(lt, 0.7 + k * 0.12, 0.4, E.rebote); pon(ch, { s: lerp(0.6, 1, e), o: cl(e * 2) }); });
    }, i % 2 ? 'izq' : 'der');
  });

  // ---- 4. Para quién (un golpe por perfil) ----
  const perfiles = [['persona', '¿Trabajas <m>solo?</m>', 'Agenda, fichas y cobros sin complicarte.', 'papel'],
    ['equipo', '¿Son <m>dos o tres?</m>', 'Cada odontólogo con su propia agenda.', 'menta'],
    ['clinica', '¿Tienes una <m>clínica?</m>', 'Recepción, caja, inventario y laboratorio.', 'papel']];
  perfiles.forEach(([ic, t, s, bg], k) => {
    escena(30 + k, 31 + k, bg, (el) => {
      const cy = VERT ? 600 : 230;
      const i = h(`<div class="abs" style="left:50%;top:${cy}px;margin-left:-80px">${icono(ic, 160, C.verde)}</div>`);
      const tt = texto(t, 'titulo', `left:40px;right:40px;text-align:center;top:${cy + 220}px;font-size:${VERT ? 118 : 140}px`);
      const ss = texto(s, 'cuerpo', `left:60px;right:60px;text-align:center;top:${cy + (VERT ? 520 : 420)}px;font-size:${VERT ? 42 : 38}px;opacity:.75`);
      [i, tt, ss].forEach((e) => el.appendChild(e)); return { i, tt, ss };
    }, (lt, st) => {
      pon(st.i, { s: lerp(0.4, 1, pr(lt, 0, 0.4, E.rebote)), o: pr(lt, 0, 0.1) });
      animarTexto(st.tt, lt, 0.05, { paso: 0.06, dy: 60, marcaEn: 0.35 });
      animarTexto(st.ss, lt, 0.3, { paso: 0.02, dy: 20 });
    }, k ? (k % 2 ? 'izq' : 'der') : 'der');
  });
  escena(33, 34, 'tinta', (el) => {
    const tt = texto(`Es para <m>ti.</m>`, 'titulo', `left:40px;right:40px;text-align:center;top:${VERT ? 380 : 170}px;font-size:${VERT ? 150 : 160}px`);
    el.appendChild(tt);
    const datos = [['escudo', 'Datos protegidos'], ['nube', 'Respaldo diario'], ['dispositivos', 'Web y celular'], ['reloj', 'Listo en minutos']];
    const chips = datos.map(([ic, txt], k) => {
      const c2 = h(`<div class="abs chip" style="background:#1f2c2e;padding:${VERT ? '22px 34px' : '20px 32px'};font-size:${VERT ? 38 : 34}px;${VERT ? `left:50%;top:${760 + k * 150}px` : `left:${k % 2 ? 980 : 420}px;top:${k < 2 ? 520 : 650}px`}">${icono(ic, VERT ? 56 : 50, C.amarillo, C.tinta)}${txt}</div>`);
      el.appendChild(c2); return c2;
    });
    return { tt, chips };
  }, (lt, st) => {
    animarTexto(st.tt, lt, 0, { golpe: true, paso: 0.12, marcaEn: 0.2 });
    st.chips.forEach((c2, k) => { const e = pr(lt, 0.25 + k * 0.125, 0.3, E.rebote); pon(c2, { x: VERT ? -c2.offsetWidth / 2 : 0, s: lerp(0.5, 1, e), o: cl(e * 2) }); });
  }, 'der');

  // ---- 5. Llamado a la acción (segundo drop) ----
  escena(34, DUR, 'verde', (el) => {
    const cy = VERT ? 380 : 120;
    const logo = h(`<div class="abs" style="left:50%;top:${cy}px;margin-left:-60px">${MARCA(120, '#fff', C.verde)}</div>`);
    const tit = texto(`Agenda tu demo<br><m>gratis</m>`, 'titulo', `left:30px;right:30px;text-align:center;top:${cy + 180}px;font-size:${VERT ? 136 : 150}px`);
    const sub = texto(`Te lo mostramos con tus datos, en 15 minutos.`, 'medio', `left:60px;right:60px;text-align:center;top:${cy + (VERT ? 510 : 500)}px;font-size:${VERT ? 44 : 42}px;opacity:.9`);
    const boton = h(`<div class="abs boton" style="left:50%;top:${cy + (VERT ? 660 : 610)}px;padding:${VERT ? '34px 52px' : '30px 54px'};font-size:${VERT ? 46 : 46}px;white-space:nowrap;background:${C.amarillo};color:${C.tinta};box-shadow:0 24px 50px -20px rgba(0,0,0,.45)">${svg('chat', VERT ? 50 : 48, C.tinta)}<span>${CONTACTO}</span>${svg('flecha', VERT ? 46 : 44, C.tinta)}</div>`);
    const pie = texto(`Odontólogos independientes · Consultorios · Clínicas`, 'etiqueta', `left:30px;right:30px;text-align:center;top:${cy + (VERT ? 900 : 800)}px;font-size:${VERT ? 24 : 22}px;opacity:.8`);
    [logo, tit, sub, boton, pie].forEach((e) => el.appendChild(e));
    return { logo, tit, sub, boton, pie };
  }, (lt, s) => {
    pon(s.logo, { s: lerp(0.3, 1, pr(lt, 0, 0.5, E.rebote)), o: pr(lt, 0, 0.1) });
    animarTexto(s.tit, lt, 0.1, { golpe: true, paso: 0.14, marcaEn: 0.6 });
    animarTexto(s.sub, lt, 0.9, { paso: 0.03, dy: 20 });
    const e = pr(lt, 1.3, 0.5, E.rebote);
    const latido = 1 + 0.04 * Math.pow(Math.max(0, Math.sin((lt - 2) * Math.PI * 2)), 8) * cl(lt - 2);
    pon(s.boton, { x: -s.boton.offsetWidth / 2, s: lerp(0.5, 1, e) * latido, o: cl(e * 2) });
    animarTexto(s.pie, lt, 1.9, { paso: 0.04, dy: 14 });
  }, 'izq');
  return DUR;
}

// ===================== AVANCE «PRÓXIMAMENTE» (20 s) =====================
function teaser() {
  const DUR = 20;
  fundidoFinal = DUR - 0.9;
  escena(0, 2, 'tinta', (el) => {
    const t = texto(`Algo nuevo<br>llega a tu<br><m>consultorio.</m>`, 'titulo', `left:40px;right:40px;text-align:center;top:${VERT ? 620 : 210}px;font-size:${VERT ? 140 : 150}px`);
    el.appendChild(t); return { t };
  }, (lt, { t }) => {
    t.piezas.forEach((p, i) => { const ini = [0.1, 0.6, 0.6, 1.1][i] ?? 1.1; const kk = pr(lt, ini, 0.15, E.out5); pon(p, { s: lerp(1.3, 1, kk), o: kk }); });
    t.marcas.forEach((m) => { m.style.transform = `scaleX(${pr(lt, 1.3, 0.25, E.out5)})`; });
  });
  const cortes = [
    ['web-02-panel', 1.0, 'Tu día', 'verde'], ['app-03-agenda', 2.0, null, 'papel'], ['web-05-odontograma', 5.0, 'Odontograma', 'tinta'], ['app-04-paciente', 10.5, null, 'menta'],
    ['web-06-oportunidades', 3.5, 'WhatsApp', 'papel'], ['app-07-oportunidades', 4.5, null, 'verde'], ['web-08-finanzas', 4.5, 'Finanzas', 'tinta'], ['app-05-cartera', 4.5, null, 'papel'],
    ['web-09-comprobante', 2.5, 'Tu logo', 'verde'], ['web-10-marca', 6.0, null, 'menta'], ['web-10-marca', 8.0, 'Tu color', 'tinta'], ['app-06-finanzas', 4.5, null, 'papel'],
    ['web-07-cartera', 3.0, 'Cartera', 'verde'], ['app-02-panel', 1.5, null, 'menta'], ['web-11-legal', 1.5, 'Seguro', 'tinta'], ['app-05-cartera', 7.0, null, 'papel'],
    ['web-04-paciente', 3.0, 'Todo', 'verde'], ['web-13-busqueda', 2.5, null, 'papel'], ['web-03-agenda', 4.0, 'En un lugar', 'tinta'], ['web-02-panel', 3.0, null, 'verde'],
  ];
  cortes.forEach(([n, d, palabra, bg], i) => {
    const a = 2 + i * 0.5;
    escena(a, a + 0.5, bg, (el) => {
      const c = clip(n); const movil = n.startsWith('app');
      let disp;
      if (movil) { disp = telefono(c, VERT ? 1300 : 900); disp.style.left = (W - disp.ancho) / 2 + 'px'; disp.style.top = (VERT ? 200 : 90) + 'px'; }
      else { const ap = VERT ? 960 : 1240; disp = laptop(c, ap); disp.style.left = (W - ap - 32) / 2 + 'px'; disp.style.top = (VERT ? 520 : (palabra ? 60 : 160)) + 'px'; }
      el.appendChild(disp);
      let pal = null;
      if (palabra) { pal = texto(palabra, 'titulo', `left:0;right:0;text-align:center;top:${VERT ? 1240 : 870}px;font-size:${VERT ? 130 : 110}px`); el.appendChild(pal); }
      return { c, disp, d, pal };
    }, (lt, s) => {
      s.c.ir(s.d + lt * 1.4);
      const e = pr(lt, 0, 0.2, E.out5);
      pon(s.disp, { y: (1 - e) * 60, s: lerp(0.94, 1, e) * (1 + lt * 0.04), o: 1 });
      if (s.pal) s.pal.piezas.forEach((p) => { const k = pr(lt, 0.03, 0.14, E.out5); pon(p, { s: lerp(1.3, 1, k), o: k }); });
    });
  });
  escena(12, 16, 'papel', (el) => {
    const cy = VERT ? 640 : 250;
    const logo = h(`<div class="abs" style="left:50%;top:${cy}px;margin-left:-100px">${MARCA(200, C.verde, '#fff')}</div>`);
    const nombre = texto(`Sistema Odontológico`, 'titulo', `left:30px;right:30px;text-align:center;top:${cy + 260}px;font-size:${VERT ? 104 : 130}px`);
    const lema = texto(`Para odontólogos independientes, <m>consultorios y clínicas.</m>`, 'medio', `left:60px;right:60px;text-align:center;top:${cy + (VERT ? 520 : 420)}px;font-size:${VERT ? 46 : 44}px`);
    [logo, nombre, lema].forEach((e) => el.appendChild(e)); return { logo, nombre, lema };
  }, (lt, s) => {
    pon(s.logo, { s: lerp(0.3, 1, pr(lt, 0.1, 0.6, E.rebote)), o: pr(lt, 0.1, 0.1) });
    animarTexto(s.nombre, lt, 0.6, { paso: 0.12, dy: 60 });
    animarTexto(s.lema, lt, 1.3, { paso: 0.05, dy: 24, marcaEn: 2.0 });
  }, 'der');
  escena(16, DUR, 'tinta', (el) => {
    const t = h(`<div class="abs titulo" style="left:0;right:0;text-align:center;white-space:nowrap;top:${VERT ? 700 : 330}px;font-size:${VERT ? 118 : 180}px">${'PRÓXIMAMENTE'.split('').map((c2) => `<span class="palabra">${c2}</span>`).join('')}</div>`);
    t.piezas = [...t.querySelectorAll('.palabra')];
    const raya = h(`<div class="abs" style="left:50%;top:${VERT ? 860 : 560}px;width:${VERT ? 560 : 760}px;margin-left:-${VERT ? 280 : 380}px;height:14px;background:${C.amarillo};transform-origin:left"></div>`);
    const cta = h(`<div class="abs boton" style="left:50%;top:${VERT ? 960 : 650}px;padding:${VERT ? "24px 36px" : "28px 48px"};font-size:${VERT ? 32 : 40}px;white-space:nowrap;background:${C.amarillo};color:${C.tinta}">${svg('chat', 42, C.tinta)}<span>Reserva tu demo: ${CONTACTO}</span></div>`);
    [t, raya, cta].forEach((e) => el.appendChild(e)); return { t, raya, cta };
  }, (lt, s) => {
    s.t.piezas.forEach((p, i) => { const k = pr(lt, i * 0.04, 0.2, E.out5); pon(p, { s: lerp(1.4, 1, k), o: k }); });
    pon(s.raya, { sx: pr(lt, 0.6, 0.4, E.out5) });
    const e = pr(lt, 1.1, 0.5, E.rebote);
    pon(s.cta, { x: -s.cta.offsetWidth / 2, s: lerp(0.5, 1, e), o: cl(e * 2) });
  }, 'izq');
  return DUR;
}

const DURACION = V === 'teaser' ? teaser() : anuncio();

window.FILM = {
  dur: DURACION, W, H, fps: FPS,
  async render(t) {
    pendientes.length = 0;
    for (const e of escenas) {
      const vis = t >= e.a && t < e.b;
      e.el.style.display = vis ? 'block' : 'none';
      if (!vis) continue;
      const lt = t - e.ini;
      if (e.barrido) {
        // Entra cubriendo la escena anterior con su color.
        const k = E.io(cl((lt + 0.3) / 0.3));
        const resto = (1 - k) * 100;
        e.el.style.clipPath = e.barrido === 'der' ? `inset(0 0 0 ${resto}%)` : `inset(0 ${resto}% 0 0)`;
      } else e.el.style.clipPath = 'none';
      e.actualizar(lt, e.st);
    }
    negro.style.opacity = pr(t, fundidoFinal, 0.9, E.io);
    await Promise.all(pendientes);
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  },
};
