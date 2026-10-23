// Campaña premium del sistema. Montaje cuadro a cuadro: CAMPANA.render(t).
// ?f=h|v  formato · ?c=contacto (opcional; si no se da, no se muestra ninguno)
const Q = new URLSearchParams(location.search);
const VERT = (Q.get('f') || 'h') === 'v';
const CONTACTO = (Q.get('c') || '').trim();
const W = VERT ? 1080 : 1920, H = VERT ? 1920 : 1080;
const FPS = 30, DUR = 46;
const stage = document.getElementById('stage');
stage.style.width = W + 'px'; stage.style.height = H + 'px';

// ---------- utilidades ----------
const cl = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, k) => a + (b - a) * k;
const E = {
  lin: (t) => t,
  out: (t) => 1 - Math.pow(1 - t, 3),
  out5: (t) => 1 - Math.pow(1 - t, 5),
  inn: (t) => t * t * t,
  io: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  suave: (t) => t * t * (3 - 2 * t),
};
const pr = (t, a, d, e = E.out) => e(cl((t - a) / d));
const h = (html) => { const d = document.createElement('div'); d.innerHTML = html.trim(); return d.firstElementChild; };
const ruido = (n) => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };

// Interpola una lista de poses {t, ...valores} con curva suave entre cada par.
function pose(kf, t) {
  if (t <= kf[0].t) return kf[0];
  for (let i = 0; i < kf.length - 1; i++) {
    const a = kf[i], b = kf[i + 1];
    if (t <= b.t) {
      const k = E.io((t - a.t) / (b.t - a.t));
      const r = { t };
      for (const key of Object.keys(b)) if (key !== 't') r[key] = lerp(a[key] ?? b[key], b[key], k);
      return r;
    }
  }
  return kf.at(-1);
}

// ---------- íconos ----------
const IC = {
  diente: 'M12 2.6c-4.6 0-7.9 2.5-7.9 6.7 0 2.9.8 5.2 1.4 8.2.5 2.2.8 4.3 2.3 4.3s1.8-2 2.3-4.1c.4-1.5 1-2.3 1.9-2.3s1.5.8 1.9 2.3c.5 2.1.8 4.1 2.3 4.1s1.8-2.1 2.3-4.3c.6-3 1.4-5.3 1.4-8.2 0-4.2-3.3-6.7-7.9-6.7z',
  escudo: 'M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z',
  agenda: 'M17 12h-5v5h5v-5zM16 1v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2h-1V1h-2zm3 18H5V8h14v11z',
  dispositivos: 'M4 6h18V4H4c-1.1 0-2 .9-2 2v11H0v3h14v-3H4V6zm19 2h-6c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h6c.55 0 1-.45 1-1V9c0-.55-.45-1-1-1zm-1 9h-4v-7h4v7z',
  nube: 'M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM10 17l-3.5-3.5 1.41-1.41L10 14.17 15.18 9l1.41 1.41L10 17z',
  flecha: 'M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z',
};
const svg = (n, t, c) => `<svg viewBox="0 0 24 24" width="${t}" height="${t}" style="fill:${c};display:block"><path d="${IC[n]}"/></svg>`;
const MARCA = (t) => `<span style="display:inline-flex;align-items:center;justify-content:center;width:${t}px;height:${t}px;border-radius:${Math.round(t * 0.27)}px;background:#0d7f76;box-shadow:inset 0 1px 0 rgba(255,255,255,.25),0 30px 60px -20px rgba(13,127,118,.55)">
  <svg viewBox="0 0 24 24" width="${Math.round(t * 0.6)}" height="${Math.round(t * 0.6)}"><path fill="#fff" d="${IC.diente}"/><path d="M8.6 9.6q3.4 2.8 6.8 0" stroke="#0d7f76" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg></span>`;

// ---------- clips (secuencias de cuadros reales) ----------
const pendientes = [];
const TOTALES = window.TOTALES || {};
class Clip {
  constructor(nombre) { this.nombre = nombre; this.total = TOTALES[nombre] || 300; this.imgs = []; this.n = 0; }
  imagen() { const i = document.createElement('img'); this.imgs.push(i); return i; }
  ir(seg) {
    const n = cl(Math.floor(seg * FPS) + 1, 1, this.total);
    if (n === this.n) return;
    this.n = n;
    const src = `cuadros/${this.nombre}/${String(n).padStart(5, '0')}.jpg`;
    for (const i of this.imgs) { i.src = src; pendientes.push(i.decode().catch(() => {})); }
  }
}

// ---------- texto ----------
function texto(html, clase, estilo) {
  const el = h(`<div class="abs ${clase}" style="${estilo}"></div>`);
  const tmp = document.createElement('div'); tmp.innerHTML = html;
  const piezas = [];
  const recorrer = (nodo, destino) => {
    for (const n of [...nodo.childNodes]) {
      if (n.nodeType === 3) {
        n.textContent.split(/(\s+)/).forEach((p) => {
          if (!p) return;
          if (/^\s+$/.test(p)) { destino.appendChild(document.createTextNode(' ')); return; }
          const s = document.createElement('span'); s.className = 'palabra'; s.textContent = p; destino.appendChild(s); piezas.push(s);
        });
      } else if (n.nodeName === 'BR') destino.appendChild(document.createElement('br'));
      else { const c = n.cloneNode(false); destino.appendChild(c); recorrer(n, c); }
    }
  };
  recorrer(tmp, el);
  el.piezas = piezas;
  return el;
}
// Entrada palabra por palabra y salida suave (sin desenfoques exagerados).
function animar(el, lt, ini, fin, { paso = 0.045, dur = 0.6, dy = 26 } = {}) {
  const sal = fin == null ? 0 : pr(lt, fin, 0.35, E.inn);
  el.piezas.forEach((p, i) => {
    const k = pr(lt, ini + i * paso, dur, E.out5);
    p.style.transform = `translate3d(0,${(1 - k) * dy - sal * 14}px,0)`;
    p.style.opacity = k * (1 - sal);
  });
}
const fade = (el, o, y = 0, s = 1) => { el.style.opacity = o; el.style.transform = `translate3d(0,${y}px,0) scale(${s})`; };

// ---------- escenario ----------
const fondo = h(`<div class="capa"></div>`); stage.appendChild(fondo);
// Luz ambiental muy sutil (un solo tono de la marca) y piso.
const luz = h(`<div class="abs" style="width:${W * 1.3}px;height:${W * 1.3}px;border-radius:50%;background:radial-gradient(circle,rgba(13,127,118,.22),transparent 60%)"></div>`); fondo.appendChild(luz);
const piso = h(`<div class="abs" style="left:0;right:0;bottom:0;height:${H * 0.35}px;background:linear-gradient(180deg,transparent,rgba(255,255,255,.025))"></div>`); fondo.appendChild(piso);
const particulas = [];
for (let i = 0; i < 34; i++) {
  const t = 1.5 + ruido(i) * 3; const p = h(`<div class="particula" style="width:${t}px;height:${t}px"></div>`);
  fondo.appendChild(p); particulas.push({ p, x: ruido(i + 9) * W, y: ruido(i + 21) * H, v: 6 + ruido(i + 33) * 14, o: 0.12 + ruido(i + 45) * 0.3, f: ruido(i + 57) * 6 });
}
const mundo = h(`<div class="mundo"></div>`); stage.appendChild(mundo);
const sombra = h(`<div class="capa" style="pointer-events:none;opacity:0;background:${VERT ? 'none' : 'linear-gradient(90deg,rgba(8,16,17,.94) 0,rgba(8,16,17,.82) 26%,rgba(8,16,17,0) 44%)'}"></div>`); stage.appendChild(sombra);
const textos = h(`<div class="capa"></div>`); stage.appendChild(textos);
stage.appendChild(h(`<div class="capa" style="pointer-events:none;background:radial-gradient(120% 90% at 50% 45%,transparent 60%,rgba(0,0,0,.5))"></div>`));
const negro = h(`<div class="capa" style="background:#000;pointer-events:none"></div>`); stage.appendChild(negro);

// ---------- dispositivos ----------
const SW = VERT ? 960 : 1240, SH = Math.round(SW * 9 / 16);
const laptop = h(`<div class="laptop" style="width:${SW + 28}px;left:0;top:0"><div class="tapa"><span class="camara"></span><div class="pantalla" style="height:${SH}px"></div></div><div class="base"></div></div>`);
mundo.appendChild(laptop);
const pantalla = laptop.querySelector('.pantalla');
const brillo = h(`<div class="brillo"></div>`);
const PH = VERT ? 600 : 780, PWd = Math.round(PH * 0.4618);
const telefono = h(`<div class="telefono" style="width:${PWd}px;height:${PH}px;left:0;top:0"><div class="pantalla"><div class="isla"></div></div></div>`);
mundo.appendChild(telefono);
const pantallaTel = telefono.querySelector('.pantalla');

// Segmentos de pantalla: [desde, hasta, toma, inicio en la toma, velocidad]
const T_FUNC = 10, D_FUNC = 3;
const FUNC = [
  { k: 'Agenda', t: 'Agenda sin choques', s: 'Cada profesional con su horario y sus citas.', web: ['web-03-agenda', 1.4, 1.3], f: [0.55, 0.55], movil: ['app-03-agenda', 1.4, 1.2] },
  { k: 'Odontograma', t: 'Odontograma digital', s: 'Registra hallazgos por pieza y guarda cada versión.', web: ['web-05-odontograma', 2.0, 2.0], f: [0.43, 0.56], movil: ['app-04-paciente', 10.4, 1.0] },
  { k: 'Oportunidades', t: 'Sabe a quién escribir hoy', s: 'Citas por confirmar, saldos y pacientes por recuperar, con el mensaje listo para WhatsApp.', web: ['web-06-oportunidades', 2.2, 1.3], f: [0.56, 0.42], movil: ['app-07-oportunidades', 4.2, 1.2] },
  { k: 'Cartera', t: 'Cobros y saldos al día', s: 'Cuánto abonó cada paciente y cuánto le falta.', web: ['web-07-cartera', 2.0, 1.4], f: [0.52, 0.36], movil: ['app-05-cartera', 4.0, 1.2] },
  { k: 'Finanzas', t: 'Finanzas claras', s: 'Ingresos, gastos fijos y proyección de caja.', web: ['web-08-finanzas', 4.2, 1.4], f: [0.55, 0.42], movil: ['app-06-finanzas', 4.4, 1.1] },
  { k: 'Documentos', t: 'Comprobantes con tu logo', s: 'Recibos, estados de cuenta y certificados listos para imprimir.', web: ['web-09-comprobante', 1.0, 1.6], f: [0.5, 0.3] },
  { k: 'Personalización', t: 'Tu marca en todo el sistema', s: 'Elige el logo y el color de tu consulta.', web: ['web-10-marca', 5.2, 1.3], f: [0.5, 0.48] },
];
const SEG_WEB = [
  [5.0, 10.0, 'web-02-panel', 0.6, 1.0],
  ...FUNC.map((f, i) => [T_FUNC + i * D_FUNC, T_FUNC + (i + 1) * D_FUNC, ...f.web]),
  [31.0, 34.0, 'web-05-odontograma', 15.4, 0.6],
  [34.0, 37.6, 'web-07-cartera', 2.0, 1.3],
];
const SEG_TEL = [
  ...(VERT ? FUNC.map((f, i) => f.movil ? [T_FUNC + i * D_FUNC, T_FUNC + (i + 1) * D_FUNC, ...f.movil] : null).filter(Boolean) : []),
  [31.0, 34.0, 'app-04-paciente', 10.6, 1.0],
  [34.0, 37.6, 'app-05-cartera', 4.0, 1.2],
];
const capas = (segs, destino) => segs.map(([a, b, n, d, v]) => { const c = new Clip(n); const img = c.imagen(); destino.appendChild(img); return { a, b, c, d, v, img }; });
const capasWeb = capas(SEG_WEB, pantalla);
const capasTel = capas(SEG_TEL, pantallaTel);
pantalla.appendChild(brillo);
function pantallas(t, lista) {
  for (const s of lista) {
    const vis = t >= s.a - 0.01 && t < s.b + 0.35;
    s.img.style.display = vis ? 'block' : 'none';
    if (!vis) continue;
    s.img.style.opacity = s.a <= 5 ? pr(t, 5.35, 0.6, E.out) : pr(t, s.a, 0.32, E.io);
    s.c.ir(s.d + Math.max(0, t - s.a) * s.v);
  }
}

// Lupas (formato vertical, funciones sin toma del celular): zona ampliada de la misma pantalla.
const lupas = VERT ? FUNC.map((f, i) => {
  if (f.movil) return null;
  const lw = 360, lh = 470, iw = 1500, ih = iw * 9 / 16;
  const c = new Clip(f.web[0]); const img = c.imagen();
  const el = h(`<div class="lupa" style="width:${lw}px;height:${lh}px;left:${W - 70 - lw}px;top:1040px;opacity:0"></div>`);
  img.style.cssText = `width:${iw}px;height:${ih}px;left:${cl(lw / 2 - f.f[0] * iw, lw - iw, 0)}px;top:${cl(lh / 2 - f.f[1] * ih, lh - ih, 0)}px`;
  el.appendChild(img); textos.appendChild(el);
  return { el, c, a: T_FUNC + i * D_FUNC, f };
}).filter(Boolean) : [];

// Poses de la laptop y del celular a lo largo del video.
const POS_L = VERT
  ? [
      { t: 5.0, x: 46, y: 420, s: 0.86, rx: 26, ry: -18, o: 0 },
      { t: 6.3, x: 46, y: 360, s: 0.94, rx: 8, ry: -6, o: 1 },
      { t: 9.2, x: 46, y: 340, s: 0.97, rx: 0, ry: 0, o: 1 },
      { t: 10.0, x: 46, y: 250, s: 1, rx: 0, ry: 0, o: 1 },
      { t: 30.8, x: 46, y: 250, s: 1, rx: 0, ry: 0, o: 1 },
      { t: 31.8, x: 46, y: 330, s: 0.93, rx: 0, ry: 0, o: 1 },
      { t: 36.7, x: 46, y: 330, s: 0.94, rx: 0, ry: 0, o: 1 },
      { t: 37.3, x: 46, y: 300, s: 0.9, rx: 0, ry: 0, o: 0 },
    ]
  : [
      { t: 5.0, x: 312, y: 190, s: 0.84, rx: 24, ry: -22, o: 0 },
      { t: 6.3, x: 312, y: 115, s: 0.9, rx: 8, ry: -8, o: 1 },
      { t: 9.2, x: 312, y: 100, s: 0.93, rx: 0, ry: 0, o: 1 },
      { t: 10.0, x: 600, y: 150, s: 0.93, rx: 0, ry: 0, o: 1 },
      { t: 30.8, x: 600, y: 150, s: 0.93, rx: 0, ry: 0, o: 1 },
      { t: 31.8, x: 110, y: 180, s: 0.82, rx: 2, ry: 12, o: 1 },
      { t: 36.7, x: 125, y: 180, s: 0.83, rx: 2, ry: 10, o: 1 },
      { t: 37.3, x: 125, y: 220, s: 0.8, rx: 2, ry: 10, o: 0 },
    ];
const POS_T = VERT
  ? [
      { t: 9.6, x: 750, y: 1080, s: 0.92, ry: 0, o: 0 },
      { t: 10.4, x: 724, y: 1030, s: 1, ry: 0, o: 1 },
      { t: 30.8, x: 724, y: 1030, s: 1, ry: 0, o: 1 },
      { t: 31.8, x: (W - PWd * 1.12) / 2, y: 1000, s: 1.12, ry: 0, o: 1 },
      { t: 36.7, x: (W - PWd * 1.12) / 2, y: 990, s: 1.12, ry: 0, o: 1 },
      { t: 37.3, x: (W - PWd * 1.12) / 2, y: 1040, s: 1.08, ry: 0, o: 0 },
    ]
  : [
      { t: 30.9, x: 1560, y: 230, s: 0.94, ry: -16, o: 0 },
      { t: 31.9, x: 1330, y: 130, s: 1, ry: -8, o: 1 },
      { t: 36.7, x: 1320, y: 130, s: 1, ry: -6, o: 1 },
      { t: 37.3, x: 1320, y: 170, s: 0.97, ry: -6, o: 0 },
    ];
const dispositivo = (el, p) => {
  el.style.transform = `translate3d(${p.x}px,${p.y}px,0) perspective(2400px) rotateX(${p.rx ?? 0}deg) rotateY(${p.ry ?? 0}deg) scale(${p.s})`;
  el.style.transformOrigin = '0 0';
  el.style.opacity = p.o;
  el.style.display = p.o < 0.005 ? 'none' : 'block';
};

// ---------- escenas de texto ----------
const escenas = [];
const escena = (a, b, crear, actualizar) => { const el = h(`<div class="capa" style="display:none"></div>`); textos.appendChild(el); escenas.push({ a, b, el, st: crear(el) || {}, actualizar }); };

// 1. Apertura: línea de luz, logo, nombre y frase.
escena(0, 5.1, (el) => {
  const cy = VERT ? 800 : 400;
  const linea = h(`<div class="linea" style="left:${W * 0.15}px;width:${W * 0.7}px;top:${cy + 90}px"></div>`);
  const halo = h(`<div class="abs" style="left:50%;top:${cy + 90}px;width:700px;height:700px;margin:-350px 0 0 -350px;border-radius:50%;background:radial-gradient(circle,rgba(60,196,180,.18),transparent 60%)"></div>`);
  const logo = h(`<div class="abs" style="left:50%;top:${cy}px;margin-left:-${VERT ? 85 : 80}px">${MARCA(VERT ? 170 : 160)}</div>`);
  const nombre = h(`<div class="abs marcaTexto" style="left:0;right:0;text-align:center;top:${cy + (VERT ? 230 : 210)}px;font-size:${VERT ? 80 : 92}px;white-space:nowrap">Sistema Odontológico</div>`);
  const frase = texto(`Toda tu consulta dental.${VERT ? '<br>' : ' '}Un solo sistema.`, 'cuerpo', `left:60px;right:60px;text-align:center;top:${cy + (VERT ? 360 : 340)}px;font-size:${VERT ? 40 : 34}px;color:#c4d4d3`);
  [halo, linea, logo, nombre, frase].forEach((e) => el.appendChild(e));
  return { linea, halo, logo, nombre, frase };
}, (lt, s) => {
  const sal = pr(lt, 4.55, 0.5, E.inn);
  const l = pr(lt, 0.3, 1.0, E.out5), lc = pr(lt, 1.3, 0.5, E.io);
  s.linea.style.transform = `scaleX(${l * (1 - lc)})`; s.linea.style.opacity = 1 - lc;
  fade(s.halo, pr(lt, 1.2, 0.8) * (1 - sal) * (0.8 + 0.2 * Math.sin(lt * 2)), 0, lerp(0.6, 1, pr(lt, 1.2, 1.2)));
  const k = pr(lt, 1.3, 0.9, E.out5);
  fade(s.logo, k * (1 - sal), (1 - k) * 20 - sal * 20, lerp(0.78, 1, k));
  const n = pr(lt, 2.0, 1.2, E.out5);
  s.nombre.style.letterSpacing = `${lerp(0.32, -0.02, n)}em`; fade(s.nombre, n * (1 - sal), -sal * 20);
  animar(s.frase, lt, 3.0, 4.55, { paso: 0.06 });
});

// 2. Presentación del producto.
escena(5.0, 9.9, (el) => {
  const tit = texto('Gestión dental completa', 'titulo', VERT ? 'left:60px;right:60px;text-align:center;top:1050px;font-size:72px' : 'left:0;right:0;text-align:center;top:930px;font-size:44px');
  const sub = texto('Agenda, pacientes, historia clínica, cobros y finanzas.', 'cuerpo', VERT ? 'left:80px;right:80px;text-align:center;top:1160px;font-size:36px' : 'left:0;right:0;text-align:center;top:992px;font-size:26px');
  el.appendChild(tit); el.appendChild(sub); return { tit, sub };
}, (lt, s) => { animar(s.tit, lt, 1.2, 4.35, { paso: 0.07 }); animar(s.sub, lt, 1.7, 4.35, { paso: 0.025 }); });

// 3. Demostración: cada función con su leyenda.
FUNC.forEach((f, i) => {
  const a = T_FUNC + i * D_FUNC;
  escena(a, a + D_FUNC, (el) => {
    const x = VERT ? 70 : 100, y = VERT ? 1040 : 560, ancho = VERT ? (f.movil ? 600 : 560) : 430;
    const cont = h(`<div class="abs etiqueta" style="left:${x}px;top:${y}px;font-size:${VERT ? 22 : 17}px;display:flex;align-items:center;gap:14px"><span>${String(i + 1).padStart(2, '0')} / ${String(FUNC.length).padStart(2, '0')}</span><span style="width:46px;height:1.5px;background:currentColor;opacity:.6"></span><span>${f.k}</span></div>`);
    const tit = texto(f.t, 'titulo', `left:${x}px;width:${ancho}px;top:${y + (VERT ? 50 : 42)}px;font-size:${VERT ? 62 : 54}px`);
    const sub = texto(f.s, 'cuerpo', `left:${x}px;width:${ancho - (VERT ? 40 : 10)}px;top:${y + (VERT ? (f.t.length > 18 ? 200 : 130) : (f.t.length > 18 ? 172 : 112))}px;font-size:${VERT ? 32 : 24}px`);
    [cont, tit, sub].forEach((e) => el.appendChild(e));
    return { cont, tit, sub };
  }, (lt, s) => {
    // La descripción va siempre debajo del título, mida lo que mida.
    s.sub.style.top = (s.tit.offsetTop + s.tit.offsetHeight + (VERT ? 22 : 18)) + 'px';
    const sal = pr(lt, D_FUNC - 0.4, 0.35, E.inn);
    fade(s.cont, pr(lt, 0.25, 0.5) * (1 - sal), (1 - pr(lt, 0.25, 0.5)) * 12);
    animar(s.tit, lt, 0.35, D_FUNC - 0.4, { paso: 0.06 });
    animar(s.sub, lt, 0.6, D_FUNC - 0.4, { paso: 0.018, dy: 16 });
  });
});

// 4. Experiencia: web y app móvil, con los mismos datos.
escena(31.0, 37.2, (el) => {
  const pos = VERT ? 'left:70px;right:70px;text-align:center;top:150px' : 'left:0;right:0;text-align:center;top:58px';
  const cont = h(`<div class="abs etiqueta" style="${pos};font-size:${VERT ? 22 : 17}px">Web y app móvil</div>`);
  const tit = texto('Los mismos datos, donde estés.', 'titulo', VERT ? 'left:60px;right:60px;text-align:center;top:200px;font-size:58px' : 'left:0;right:0;text-align:center;top:92px;font-size:46px');
  const sub = texto('La computadora del consultorio y tu celular, conectados al mismo sistema.', 'cuerpo', VERT ? 'left:90px;right:90px;text-align:center;top:1690px;font-size:30px' : 'left:0;right:0;text-align:center;top:990px;font-size:24px');
  [cont, tit, sub].forEach((e) => el.appendChild(e)); return { cont, tit, sub };
}, (lt, s) => {
  fade(s.cont, pr(lt, 0.6, 0.5) * (1 - pr(lt, 5.8, 0.35)));
  animar(s.tit, lt, 0.75, 5.8, { paso: 0.06 });
  animar(s.sub, lt, 1.4, 5.8, { paso: 0.02, dy: 14 });
});

// 5. Beneficios reales.
escena(37.2, 41.05, (el) => {
  const tit = texto('Pensado para el día a día de tu consulta', 'titulo', VERT ? 'left:70px;right:70px;text-align:center;top:300px;font-size:64px' : 'left:0;right:0;text-align:center;top:170px;font-size:52px');
  const datos = [['escudo', 'Historia clínica digital y segura', 'Cada acceso a una ficha queda registrado.'], ['agenda', 'Agenda, cobros y finanzas juntos', 'Todo en un solo lugar.'], ['dispositivos', 'Web y app móvil', 'La misma información en ambas.'], ['nube', 'Respaldo diario automático', 'Tu información, protegida.']];
  const cards = datos.map(([ic, t, d], k) => {
    const pos = VERT ? `left:80px;right:80px;top:${560 + k * 200}px` : `left:${k % 2 ? 980 : 260}px;top:${k < 2 ? 330 : 520}px;width:680px`;
    const c = h(`<div class="abs tarjeta" style="${pos};display:flex;align-items:center;gap:24px;padding:${VERT ? '30px 34px' : '28px 32px'}"><span class="icono" style="width:${VERT ? 76 : 68}px;height:${VERT ? 76 : 68}px">${svg(ic, VERT ? 38 : 34, '#3cc4b4')}</span><div><div class="titulo" style="font-size:${VERT ? 36 : 30}px;letter-spacing:-.02em">${t}</div><div class="cuerpo" style="font-size:${VERT ? 27 : 22}px;margin-top:6px">${d}</div></div></div>`);
    el.appendChild(c); return c;
  });
  const pie = texto('Para odontólogos independientes, consultorios y clínicas.', 'cuerpo', VERT ? 'left:80px;right:80px;text-align:center;top:1400px;font-size:32px;color:#c4d4d3' : 'left:0;right:0;text-align:center;top:760px;font-size:28px;color:#c4d4d3');
  el.appendChild(tit); el.appendChild(pie);
  return { tit, cards, pie };
}, (lt, s) => {
  const sal = pr(lt, 3.45, 0.35, E.inn);
  animar(s.tit, lt, 0.1, 3.45, { paso: 0.05 });
  s.cards.forEach((c, k) => { const e = pr(lt, 0.4 + k * 0.18, 0.7, E.out5); fade(c, e * (1 - sal), (1 - e) * 30 - sal * 10); });
  animar(s.pie, lt, 1.5, 3.45, { paso: 0.025, dy: 14 });
});

// 6. Cierre comercial.
escena(41.0, DUR, (el) => {
  const cy = VERT ? 640 : 250;
  const halo = h(`<div class="abs" style="left:50%;top:${cy + 80}px;width:800px;height:800px;margin:-400px 0 0 -400px;border-radius:50%;background:radial-gradient(circle,rgba(60,196,180,.16),transparent 60%)"></div>`);
  const logo = h(`<div class="abs" style="left:50%;top:${cy}px;margin-left:-70px">${MARCA(140)}</div>`);
  const nombre = h(`<div class="abs marcaTexto" style="left:0;right:0;text-align:center;top:${cy + 180}px;font-size:${VERT ? 76 : 80}px;white-space:nowrap">Sistema Odontológico</div>`);
  const frase = texto('Conócelo funcionando con los datos de tu consulta.', 'cuerpo', `left:70px;right:70px;text-align:center;top:${cy + (VERT ? 300 : 290)}px;font-size:${VERT ? 36 : 32}px;color:#c4d4d3`);
  const boton = h(`<div class="abs boton" style="left:50%;top:${cy + (VERT ? 450 : 390)}px;padding:${VERT ? '26px 46px' : '24px 46px'};font-size:${VERT ? 36 : 32}px">Solicita una demostración${svg('flecha', VERT ? 36 : 32, '#081011')}</div>`);
  const contacto = CONTACTO ? texto(CONTACTO, 'titulo', `left:0;right:0;text-align:center;top:${cy + (VERT ? 590 : 520)}px;font-size:${VERT ? 40 : 34}px;color:#3cc4b4`) : null;
  [halo, logo, nombre, frase, boton, contacto].filter(Boolean).forEach((e) => el.appendChild(e));
  return { halo, logo, nombre, frase, boton, contacto };
}, (lt, s) => {
  fade(s.halo, pr(lt, 0, 1.2) * (0.85 + 0.15 * Math.sin(lt * 2)), 0, lerp(0.7, 1, pr(lt, 0, 1.5)));
  const k = pr(lt, 0.05, 0.9, E.out5); fade(s.logo, k, (1 - k) * 20, lerp(0.8, 1, k));
  const n = pr(lt, 0.4, 1.1, E.out5); s.nombre.style.letterSpacing = `${lerp(0.25, -0.02, n)}em`; fade(s.nombre, n);
  animar(s.frase, lt, 1.0, null, { paso: 0.035 });
  const b = pr(lt, 1.6, 0.8, E.out5);
  s.boton.style.opacity = b; s.boton.style.transform = `translate3d(-50%,${(1 - b) * 20}px,0)`;
  if (s.contacto) animar(s.contacto, lt, 2.1, null, { paso: 0.05 });
});

// ---------- render ----------
window.CAMPANA = {
  dur: DUR, W, H, fps: FPS,
  async render(t) {
    pendientes.length = 0;
    // Fondo vivo y discreto.
    luz.style.transform = `translate(${W * 0.5 - W * 0.65 + Math.sin(t * 0.21) * W * 0.12}px,${H * 0.42 - W * 0.65 + Math.cos(t * 0.17) * H * 0.08}px)`;
    for (const q of particulas) {
      const y = ((q.y - t * q.v) % H + H) % H;
      q.p.style.transform = `translate(${q.x + Math.sin(t * 0.5 + q.f) * 12}px,${y}px)`;
      q.p.style.opacity = q.o * (0.6 + 0.4 * Math.sin(t * 0.9 + q.f));
    }
    // Dispositivos.
    const pl = pose(POS_L, t);
    mundo.style.transform = 'none';
    dispositivo(laptop, pl);
    // Empuje lento durante las funciones en vertical (la pantalla se ve completa).
    if (VERT && t >= T_FUNC && t < 31) { const lt = (t - T_FUNC) % D_FUNC; laptop.style.transform += ` scale(${1 + 0.025 * E.io(lt / D_FUNC)})`; }
    dispositivo(telefono, pose(POS_T, t));
    if (VERT && t >= T_FUNC + 2 * D_FUNC && t < 31.4) {
      // Sin toma del celular para esta función: el teléfono se retira y entra la lupa.
      const i = Math.floor((t - T_FUNC) / D_FUNC), lt = t - T_FUNC - i * D_FUNC;
      let k = 1;
      if (i < FUNC.length && !FUNC[i].movil) k = FUNC[i - 1]?.movil ? 1 - pr(lt, 0, 0.3, E.io) : 0;
      if (t >= 31) k = pr(t, 31, 0.4, E.io);
      telefono.style.opacity = Number(telefono.style.opacity) * k;
    }
    pantallas(t, capasWeb); pantallas(t, capasTel);
    // Destello de la pantalla al encenderse y en cada cambio de función.
    const destellos = [5.4, ...FUNC.map((_, i) => T_FUNC + i * D_FUNC + 0.1), 31.2];
    let br = -1; for (const d of destellos) if (t >= d && t < d + 1.0) br = (t - d) / 1.0;
    brillo.style.opacity = br < 0 ? 0 : Math.sin(Math.PI * br) * 0.9;
    brillo.style.transform = `translateX(${lerp(-60, 60, br < 0 ? 0 : br)}%)`;

    // Cámara: en horizontal, cada función empieza con la pantalla completa y
    // luego se acerca con suavidad a lo importante.
    let sombraK = 0;
    if (!VERT && t >= T_FUNC && t < 31) {
      const i = Math.floor((t - T_FUNC) / D_FUNC), lt = t - T_FUNC - i * D_FUNC, f = FUNC[i];
      const k = E.io(cl((lt - 0.55) / 1.25)) * (1 - E.io(cl((lt - 2.35) / 0.55)));
      if (k > 0) {
        const r = pantalla.getBoundingClientRect(), sr = stage.getBoundingClientRect();
        const px = r.left - sr.left + f.f[0] * r.width, py = r.top - sr.top + f.f[1] * r.height;
        const Z = 1.42, qx = W * 0.66, qy = H * 0.5;
        const s = lerp(1, Z, k), tx = lerp(0, qx - px * Z, k), ty = lerp(0, qy - py * Z, k);
        mundo.style.transform = `translate3d(${tx}px,${ty}px,0) scale(${s})`;
      }
      sombraK = k;
    }
    sombra.style.opacity = sombraK;
    for (const l of lupas) {
      const lt = t - l.a, vis = lt >= 0 && lt < D_FUNC;
      l.el.style.display = vis ? 'block' : 'none';
      if (!vis) continue;
      l.c.ir(l.f.web[1] + lt * l.f.web[2]);
      const e = pr(lt, 0.3, 0.7, E.out5), sal = pr(lt, D_FUNC - 0.4, 0.35, E.inn);
      l.el.style.opacity = e * (1 - sal);
      l.el.style.transform = `translate3d(0,${(1 - e) * 40}px,0) scale(${lerp(0.94, 1, e)})`;
    }
    // Textos.
    for (const e of escenas) {
      const vis = t >= e.a && t < e.b;
      e.el.style.display = vis ? 'block' : 'none';
      if (vis) e.actualizar(t - e.a, e.st);
    }
    negro.style.opacity = Math.max(1 - pr(t, 0, 0.8, E.out), pr(t, DUR - 0.9, 0.9, E.io));
    await Promise.all(pendientes);
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  },
};
