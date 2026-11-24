import { TOOTH_CONDITION_BY_CODE } from './tooth-conditions';

export type Vec3 = [number, number, number];
export type Cara = 'mesial' | 'distal' | 'vestibular' | 'lingual' | 'oclusal';
export const CARAS: Cara[] = ['mesial', 'distal', 'vestibular', 'lingual', 'oclusal'];

export const MAT = { esmalte: 0, encia: 1, metal: 2, raiz: 3, brillo: 4 } as const;

export interface Hallazgo {
  fdi_number: string;
  surface: string;
  condition: string;
}

export interface Malla {
  posiciones: Float32Array;
  normales: Float32Array;
  colores: Float32Array;
  /** Por vértice: tipo de material, oclusión ambiental y cara (−1 si no aplica). */
  materiales: Float32Array;
  indices: Uint16Array;
}

export interface Pieza extends Malla {
  fdi: string;
  nombre: string;
  superior: boolean;
  caras: Int8Array;
  centro: Vec3;
  radio: number;
  ancla: Vec3;
  afuera: Vec3;
  ausente: boolean;
  movilidad: boolean;
  raiz: Malla | null;
  colorMarca: string | null;
}

export interface Boca {
  piezas: Pieza[];
  encias: (Malla & { superior: boolean })[];
}

type Tipo = 'incisivo' | 'canino' | 'premolar' | 'molar';

interface Medida {
  ancho: number;
  fondo: number;
  alto: number;
  tipo: Tipo;
  raices: number;
  largoRaiz: number;
}

const m = (ancho: number, fondo: number, alto: number, tipo: Tipo, raices: number, largoRaiz: number): Medida => ({
  ancho, fondo, alto, tipo, raices, largoRaiz,
});

const SUPERIOR: Medida[] = [
  m(0.86, 0.7, 1.05, 'incisivo', 1, 1.35),
  m(0.66, 0.62, 0.93, 'incisivo', 1, 1.3),
  m(0.78, 0.8, 1.08, 'canino', 1, 1.7),
  m(0.7, 0.9, 0.84, 'premolar', 2, 1.3),
  m(0.68, 0.88, 0.8, 'premolar', 1, 1.3),
  m(1.02, 1.1, 0.74, 'molar', 3, 1.25),
  m(0.94, 1.06, 0.7, 'molar', 3, 1.2),
  m(0.86, 1.0, 0.66, 'molar', 3, 1.05),
];
const INFERIOR: Medida[] = [
  m(0.54, 0.6, 0.92, 'incisivo', 1, 1.25),
  m(0.6, 0.62, 0.95, 'incisivo', 1, 1.3),
  m(0.7, 0.76, 1.04, 'canino', 1, 1.6),
  m(0.7, 0.8, 0.84, 'premolar', 1, 1.35),
  m(0.72, 0.84, 0.8, 'premolar', 1, 1.35),
  m(1.1, 1.02, 0.72, 'molar', 2, 1.3),
  m(1.04, 1.0, 0.7, 'molar', 2, 1.25),
  m(1.0, 0.96, 0.66, 'molar', 2, 1.1),
];
const TEMPORAL: Medida[] = [
  m(0.62, 0.56, 0.72, 'incisivo', 1, 0.95),
  m(0.54, 0.52, 0.68, 'incisivo', 1, 0.9),
  m(0.64, 0.64, 0.76, 'canino', 1, 1.1),
  m(0.76, 0.8, 0.6, 'molar', 2, 0.85),
  m(0.92, 0.92, 0.6, 'molar', 2, 0.9),
];

const NOMBRES_PERM = ['incisivo central', 'incisivo lateral', 'canino', 'primer premolar', 'segundo premolar', 'primer molar', 'segundo molar', 'tercer molar'];
const NOMBRES_TEMP = ['incisivo central temporal', 'incisivo lateral temporal', 'canino temporal', 'primer molar temporal', 'segundo molar temporal'];
const LADOS: Record<string, string> = {
  '1': 'superior derecho', '2': 'superior izquierdo', '3': 'inferior izquierdo', '4': 'inferior derecho',
  '5': 'superior derecho', '6': 'superior izquierdo', '7': 'inferior izquierdo', '8': 'inferior derecho',
};

export function nombrePieza(fdi: string): string {
  const q = fdi[0];
  const i = Number(fdi[1]) - 1;
  const base = Number(q) >= 5 ? NOMBRES_TEMP[i] : NOMBRES_PERM[i];
  if (!base) return `Pieza ${fdi}`;
  return `${base[0].toUpperCase()}${base.slice(1)} ${LADOS[q] ?? ''}`.trim();
}

export function hex(c: string): Vec3 {
  const n = parseInt(c.replace('#', ''), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
}

const mezclar = (a: Vec3, b: Vec3, t: number): Vec3 => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
const sumar = (a: Vec3, b: Vec3): Vec3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const escalar = (a: Vec3, k: number): Vec3 => [a[0] * k, a[1] * k, a[2] * k];
const restar = (a: Vec3, b: Vec3): Vec3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const cruz = (a: Vec3, b: Vec3): Vec3 => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const punto = (a: Vec3, b: Vec3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const suave = (a: number, b: number, x: number) => {
  const t = clamp((x - a) / (b - a));
  return t * t * (3 - 2 * t);
};
function normal(a: Vec3): Vec3 {
  const l = Math.hypot(a[0], a[1], a[2]) || 1;
  return [a[0] / l, a[1] / l, a[2] / l];
}
function ruido(x: number, y: number, z: number): number {
  const s = Math.sin(x * 12.9898 + y * 78.233 + z * 37.719) * 43758.5453;
  return s - Math.floor(s);
}

interface Marco {
  centro: Vec3;
  distal: Vec3;
  vestibular: Vec3;
}

function puntoArcada(rx: number, rz: number, lado: number, th: number): Marco {
  const centro: Vec3 = [lado * rx * Math.sin(th), 0, rz * Math.cos(th) - rz];
  const distal = normal([lado * rx * Math.cos(th), 0, -rz * Math.sin(th)]);
  const vestibular = normal([(lado * Math.sin(th)) / rx, 0, Math.cos(th) / rz]);
  return { centro, distal, vestibular };
}

function ubicar(medidas: Medida[], rx: number, rz: number, separacion = 0.025): { th: number; medio: number }[] {
  const out: { th: number; medio: number }[] = [];
  let th = 0;
  let recorrido = 0;
  let objetivo = medidas[0].ancho / 2 + separacion / 2;
  const paso = 0.0015;
  const largo = (a: number, b: number) => {
    const p = puntoArcada(rx, rz, 1, a).centro;
    const q = puntoArcada(rx, rz, 1, b).centro;
    return Math.hypot(q[0] - p[0], q[2] - p[2]);
  };
  for (let i = 0; i < medidas.length; i++) {
    while (recorrido < objetivo) {
      recorrido += largo(th, th + paso);
      th += paso;
    }
    out.push({ th, medio: 0 });
    if (i + 1 < medidas.length) objetivo += medidas[i].ancho / 2 + separacion + medidas[i + 1].ancho / 2;
  }
  for (let i = 0; i < out.length; i++) {
    const ant = i === 0 ? 0 : (out[i - 1].th + out[i].th) / 2;
    out[i].medio = out[i].th - ant;
  }
  return out;
}

const LADO = 22;
const TAPA = 14;
const SEG = 44;

function superelipse(th: number, n: number): [number, number] {
  const c = Math.cos(th);
  const s = Math.sin(th);
  return [Math.sign(c) * Math.abs(c) ** (2 / n), Math.sign(s) * Math.abs(s) ** (2 / n)];
}

function gauss(x: number, z: number, cx: number, cz: number, s2: number): number {
  return Math.exp(-((x - cx) ** 2 + (z - cz) ** 2) / s2);
}

function relieve(t: Tipo, arriba: boolean, xn: number, zn: number): number {
  if (t === 'molar') {
    const cusp = arriba
      ? gauss(xn, zn, -0.45, 0.48, 0.09) + 0.9 * gauss(xn, zn, 0.48, 0.46, 0.08) + 1.05 * gauss(xn, zn, -0.38, -0.46, 0.11) + 0.7 * gauss(xn, zn, 0.5, -0.5, 0.07)
      : gauss(xn, zn, -0.55, 0.46, 0.08) + 0.92 * gauss(xn, zn, 0.05, 0.5, 0.07) + 0.75 * gauss(xn, zn, 0.66, 0.3, 0.05) + 1.05 * gauss(xn, zn, -0.45, -0.46, 0.09) + 0.95 * gauss(xn, zn, 0.42, -0.46, 0.08);
    const surco = 0.55 * Math.exp(-(zn * zn) / 0.018) * (1 - xn * xn * 0.6) + 0.35 * Math.exp(-((xn + 0.05) ** 2) / 0.02) * (1 - zn * zn);
    return cusp - surco - 0.1;
  }
  if (t === 'premolar') {
    const cusp = gauss(xn, zn, 0, 0.46, 0.12) + (arriba ? 0.85 : 0.45) * gauss(xn, zn, 0, -0.46, 0.11);
    const surco = 0.5 * Math.exp(-((zn + 0.02) ** 2) / 0.02) * (1 - xn * xn * 0.7);
    return cusp - surco - 0.05;
  }
  return 0;
}

interface Corona {
  p: Vec3[];
  tri: number[];
  altura: number[];
  tapa: number[];
  surco: number[];
}

function corona(md: Medida, arriba: boolean): Corona {
  const p: Vec3[] = [];
  const altura: number[] = [];
  const tapa: number[] = [];
  const surco: number[] = [];
  const a0 = md.ancho / 2;
  const b0 = md.fondo / 2;
  const t = md.tipo;
  const n = t === 'molar' ? 2.9 : t === 'premolar' ? 2.5 : t === 'canino' ? 2.2 : 2.35;
  const ySide = md.alto * (t === 'incisivo' ? 0.86 : t === 'canino' ? 0.72 : t === 'premolar' ? 0.74 : 0.72);
  const anterior = t === 'incisivo' || t === 'canino';

  for (let i = 0; i <= LADO; i++) {
    const u = i / LADO;
    let s = 0.78 + 0.22 * Math.sin(Math.min(u / 0.42, 1) * (Math.PI / 2));
    s *= 1 - 0.05 * Math.max(0, (u - 0.6) / 0.4);
    for (let j = 0; j < SEG; j++) {
      const th = (j / SEG) * Math.PI * 2;
      const [cx, cz] = superelipse(th, n);
      let a = a0 * s;
      let b = b0 * s;
      if (t === 'incisivo') {
        b *= 1 - 0.42 * u;
        if (cz < 0) b *= 1 - 0.18 * Math.sin(u * Math.PI);
      }
      if (t === 'canino') {
        a *= 1 - 0.18 * u * u;
        b *= 1 - 0.22 * u;
      }
      const x = a * cx;
      const z = b * cz + (anterior ? 0.03 * u * u : 0);
      p.push([x, ySide * u, z]);
      altura.push(u * (ySide / md.alto));
      tapa.push(0);
      surco.push(0);
    }
  }

  for (let k = 1; k <= TAPA; k++) {
    const f = (k / TAPA) * (Math.PI / 2);
    const rho = Math.cos(f);
    for (let j = 0; j < SEG; j++) {
      const th = (j / SEG) * Math.PI * 2;
      const [cx, cz] = superelipse(th, n);
      const sTop = 0.95;
      let x: number;
      let z: number;
      let y: number;
      let rel = 0;
      if (t === 'incisivo') {
        x = a0 * sTop * cx * (0.9 + 0.1 * rho);
        z = b0 * sTop * (1 - 0.42) * cz * rho;
        const xn = x / a0;
        y = ySide + md.alto * 0.14 * Math.sin(f) - md.alto * 0.07 * xn ** 4 + 0.012 * Math.cos(xn * Math.PI * 3) * Math.sin(f);
      } else if (t === 'canino') {
        x = a0 * sTop * (1 - 0.18) * cx * rho;
        z = b0 * sTop * (1 - 0.22) * cz * rho;
        const xn = x / a0;
        y = ySide + md.alto * 0.3 * Math.sin(f) ** 1.25 - md.alto * 0.12 * Math.abs(xn) * (1 - rho);
      } else {
        x = a0 * sTop * cx * rho;
        z = b0 * sTop * cz * rho;
        const xn = x / a0;
        const zn = z / b0;
        const w = suave(0, 0.35, 1 - rho);
        rel = relieve(t, arriba, xn, zn) * w;
        y = ySide + md.alto * 0.1 * Math.sin(f) + rel * md.alto * 0.24;
      }
      p.push([x, y, z]);
      altura.push(Math.min(1, y / md.alto));
      tapa.push(k / TAPA);
      surco.push(rel < 0 ? -rel : 0);
    }
  }

  const tri: number[] = [];
  const filas = LADO + TAPA;
  for (let i = 0; i < filas; i++) {
    for (let j = 0; j < SEG; j++) {
      const a = i * SEG + j;
      const b = i * SEG + ((j + 1) % SEG);
      tri.push(a, a + SEG, b, b, a + SEG, b + SEG);
    }
  }
  const fondo = p.length;
  p.push([0, -0.02, 0]);
  altura.push(0);
  tapa.push(0);
  surco.push(0);
  for (let j = 0; j < SEG; j++) tri.push(j, (j + 1) % SEG, fondo);
  return { p, tri, altura, tapa, surco };
}

function raiz(md: Medida, implante: boolean): { p: Vec3[]; tri: number[] } {
  const p: Vec3[] = [];
  const tri: number[] = [];
  const a0 = md.ancho / 2;
  const b0 = md.fondo / 2;
  const R = 16;
  const S = 20;
  const raices: { ox: number; oz: number; ra: number; rb: number; largo: number }[] = implante
    ? [{ ox: 0, oz: 0, ra: Math.min(a0, b0) * 0.62, rb: Math.min(a0, b0) * 0.62, largo: md.largoRaiz * 0.85 }]
    : md.raices === 1
      ? [{ ox: 0, oz: 0, ra: a0 * 0.7, rb: b0 * 0.78, largo: md.largoRaiz }]
      : md.raices === 2 && md.tipo === 'premolar'
        ? [
            { ox: 0, oz: b0 * 0.36, ra: a0 * 0.55, rb: b0 * 0.42, largo: md.largoRaiz },
            { ox: 0, oz: -b0 * 0.36, ra: a0 * 0.5, rb: b0 * 0.4, largo: md.largoRaiz * 0.95 },
          ]
        : md.raices === 2
          ? [
              { ox: -a0 * 0.42, oz: 0, ra: a0 * 0.38, rb: b0 * 0.7, largo: md.largoRaiz },
              { ox: a0 * 0.42, oz: 0, ra: a0 * 0.34, rb: b0 * 0.66, largo: md.largoRaiz * 0.92 },
            ]
          : [
              { ox: -a0 * 0.4, oz: b0 * 0.38, ra: a0 * 0.34, rb: b0 * 0.34, largo: md.largoRaiz * 0.92 },
              { ox: a0 * 0.42, oz: b0 * 0.38, ra: a0 * 0.3, rb: b0 * 0.32, largo: md.largoRaiz * 0.86 },
              { ox: 0, oz: -b0 * 0.42, ra: a0 * 0.42, rb: b0 * 0.36, largo: md.largoRaiz },
            ];
  for (const r of raices) {
    const base = p.length;
    for (let i = 0; i <= R; i++) {
      const u = i / R;
      const y = 0.06 - r.largo * 0.86 * u;
      let s = Math.max(0, 1 - u ** 2.4) ** 0.55 * (1 - 0.28 * u);
      if (implante) s = (u < 0.85 ? 1 : 1 - (u - 0.85) / 0.15 * 0.6) * (1 + 0.09 * Math.sin(u * r.largo * 42));
      const ox = r.ox * (0.4 + 0.6 * Math.min(1, u * 3)) * (implante ? 0 : 1);
      const oz = r.oz * (0.4 + 0.6 * Math.min(1, u * 3)) * (implante ? 0 : 1);
      for (let j = 0; j < S; j++) {
        const th = (j / S) * Math.PI * 2;
        p.push([ox + r.ra * s * Math.cos(th), y, oz + r.rb * s * Math.sin(th)]);
      }
    }
    for (let i = 0; i < R; i++) {
      for (let j = 0; j < S; j++) {
        const a = base + i * S + j;
        const b = base + i * S + ((j + 1) % S);
        tri.push(a, b, a + S, b, b + S, a + S);
      }
    }
  }
  return { p, tri };
}

function normalesSuaves(p: Vec3[], tri: number[]): Vec3[] {
  const acc: Vec3[] = p.map(() => [0, 0, 0]);
  for (let k = 0; k < tri.length; k += 3) {
    const a = tri[k];
    const b = tri[k + 1];
    const c = tri[k + 2];
    const f = cruz(restar(p[b], p[a]), restar(p[c], p[a]));
    for (const v of [a, b, c]) acc[v] = sumar(acc[v], f);
  }
  return acc.map(normal);
}

function haciaAfuera(p: Vec3[], nn: Vec3[], centro: Vec3): Vec3[] {
  let s = 0;
  for (let i = 0; i < p.length; i += 7) s += punto(nn[i], restar(p[i], centro));
  return s < 0 ? nn.map((v) => escalar(v, -1)) : nn;
}

function caraDe(nl: Vec3, tapa: number): Cara {
  if (tapa > 0.35 && nl[1] > 0.35) return 'oclusal';
  if (nl[1] > 0.8) return 'oclusal';
  if (Math.abs(nl[2]) >= Math.abs(nl[0]) * 0.9) return nl[2] > 0 ? 'vestibular' : 'lingual';
  return nl[0] > 0 ? 'distal' : 'mesial';
}

const DIR_CARA: Record<Exclude<Cara, 'oclusal'>, [number, number]> = {
  mesial: [-1, 0],
  distal: [1, 0],
  vestibular: [0, 1],
  lingual: [0, -1],
};

function pesoCara(cara: Cara, nl: Vec3, altura: number, tapa: number): number {
  if (cara === 'oclusal') return suave(0.3, 0.7, nl[1]) * suave(0.55, 0.8, altura);
  const l = Math.hypot(nl[0], nl[2]) || 1;
  const [dx, dz] = DIR_CARA[cara];
  const d = (nl[0] * dx + nl[2] * dz) / l;
  return suave(0.45, 0.85, d) * suave(0.1, 0.3, altura) * (1 - suave(0.45, 0.85, nl[1])) * (1 - suave(0.5, 1, tapa));
}

function centroCara(c: Cara, md: Medida): Vec3 {
  const a = md.ancho / 2;
  const b = md.fondo / 2;
  const h = md.alto;
  switch (c) {
    case 'vestibular': return [0, h * 0.42, b * (md.tipo === 'incisivo' ? 0.75 : 0.95)];
    case 'lingual': return [0, h * 0.42, -b * 0.9];
    case 'mesial': return [-a * 0.95, h * 0.55, 0];
    case 'distal': return [a * 0.95, h * 0.55, 0];
    default: return [a * 0.08, h * 0.95, 0];
  }
}

const ORDEN_CARA = ['caries', 'fractura', 'restauracion_defectuosa', 'tratamiento_pendiente', 'restauracion', 'sellante', 'tratamiento_realizado'];
const COMPLETOS = ['implante', 'corona', 'protesis', 'puente', 'extraccion_indicada', 'endodoncia', 'diente_retenido', 'movilidad'];

const ESMALTE: Vec3 = [0.95, 0.93, 0.87];
const CUELLO: Vec3 = [0.9, 0.82, 0.64];
const BORDE: Vec3 = [0.8, 0.85, 0.89];
const DENTINA: Vec3 = [0.91, 0.84, 0.66];
const TITANIO: Vec3 = [0.7, 0.74, 0.78];
const ORO: Vec3 = [0.88, 0.71, 0.34];
const OSCURO: Vec3 = [0.22, 0.12, 0.1];

function armarPieza(
  fdi: string,
  md: Medida,
  marco: Marco,
  arriba: boolean,
  distancia: number,
  hallazgos: Hallazgo[],
): Pieza {
  const c = corona(md, arriba);
  const codigos = new Set(hallazgos.map((h) => h.condition));
  const ausente = codigos.has('ausente') || codigos.has('extraccion_realizada');
  const completo = COMPLETOS.find((k) => codigos.has(k)) ?? null;
  const implante = codigos.has('implante');
  const retenido = codigos.has('diente_retenido');

  const inclin = md.tipo === 'incisivo' ? (arriba ? 0.24 : 0.12) : md.tipo === 'canino' ? 0.1 : md.tipo === 'premolar' ? 0.02 : arriba ? -0.02 : -0.08;
  const sArco = arriba ? 1 : -1;
  const U0: Vec3 = [0, -sArco, 0];
  const O0 = marco.vestibular;
  const U = normal(sumar(escalar(U0, Math.cos(inclin)), escalar(O0, Math.sin(inclin))));
  const O = normal(sumar(escalar(O0, Math.cos(inclin)), escalar(U0, -Math.sin(inclin))));
  const T = marco.distal;
  const hundido = retenido ? md.alto * 0.7 : 0;
  const origen: Vec3 = [marco.centro[0], sArco * (distancia + md.alto + hundido), marco.centro[2]];
  const mundo = (v: Vec3): Vec3 => sumar(sumar(sumar(origen, escalar(T, v[0])), escalar(U, v[1])), escalar(O, v[2]));
  const giro = (v: Vec3): Vec3 => sumar(sumar(escalar(T, v[0]), escalar(U, v[1])), escalar(O, v[2]));

  let nl = normalesSuaves(c.p, c.tri);
  nl = haciaAfuera(c.p, nl, [0, md.alto * 0.45, 0]);

  const porCara = new Map<Cara, string | null>();
  for (const cara of CARAS) {
    const aqui = hallazgos.filter((h) => h.surface === cara || (h.surface === 'whole' && ORDEN_CARA.includes(h.condition)));
    porCara.set(cara, ORDEN_CARA.find((k) => aqui.some((h) => h.condition === k)) ?? null);
  }

  const variacion = (ruido(Number(fdi), 1.7, 3.1) - 0.5) * 0.03;
  const n = c.p.length;
  const posiciones = new Float32Array(n * 3);
  const normales = new Float32Array(n * 3);
  const colores = new Float32Array(n * 3);
  const materiales = new Float32Array(n * 3);
  const caras = new Int8Array(n);
  const anterior = md.tipo === 'incisivo' || md.tipo === 'canino';

  for (let i = 0; i < n; i++) {
    const v = c.p[i];
    const nn = nl[i];
    const h = c.altura[i];
    const cara = caraDe(nn, c.tapa[i]);
    caras[i] = CARAS.indexOf(cara);
    let col = mezclar(CUELLO, ESMALTE, suave(0.02, 0.4, h));
    if (anterior) col = mezclar(col, BORDE, suave(0.8, 1, h) * 0.55);
    col = [col[0] + variacion, col[1] + variacion, col[2] + variacion * 0.6];
    let mat: number = MAT.esmalte;
    let ao = 0.7 + 0.3 * suave(0, 0.32, h);
    if (Math.abs(nn[0]) > 0.75) ao *= 0.9;
    ao *= 1 - Math.min(0.35, c.surco[i] * 0.55);

    if (completo === 'corona') {
      col = ORO;
      mat = MAT.metal;
    } else if (implante) {
      col = [0.93, 0.94, 0.95];
      mat = MAT.brillo;
    } else if (completo === 'protesis' || completo === 'puente') {
      col = mezclar(col, hex(TOOTH_CONDITION_BY_CODE[completo].color), 0.38);
      mat = MAT.brillo;
    } else if (completo === 'extraccion_indicada') {
      col = mezclar(col, hex('#fb8c00'), 0.42);
    } else if (completo === 'endodoncia') {
      col = mezclar(col, [0.82, 0.78, 0.72], 0.4);
    } else if (completo === 'diente_retenido') {
      col = mezclar(col, hex('#a1887f'), 0.25);
    } else if (completo === 'movilidad') {
      col = mezclar(col, hex('#d81b60'), 0.18);
    }

    if (!ausente && completo !== 'corona' && !implante) {
      for (const cf of CARAS) {
        const cod = porCara.get(cf);
        if (!cod) continue;
        let w = pesoCara(cf, nn, h, c.tapa[i]);
        if (w <= 0.01) continue;
        const color = hex(TOOTH_CONDITION_BY_CODE[cod]?.color ?? '#999999');
        if (cod === 'caries') {
          const cen = centroCara(cf, md);
          const ang = Math.atan2(v[1] - cen[1], (cf === 'mesial' || cf === 'distal' ? v[2] : v[0]) - (cf === 'mesial' || cf === 'distal' ? cen[2] : cen[0]));
          const semilla = Number(fdi) * 0.37 + CARAS.indexOf(cf);
          const radio = (cf === 'mesial' || cf === 'distal' ? md.fondo : md.ancho) * (cf === 'oclusal' ? 0.34 : 0.3) * (0.82 + 0.18 * Math.sin(ang * 3 + semilla) + 0.08 * Math.sin(ang * 7 + semilla * 2));
          const dist = Math.hypot(v[0] - cen[0], v[1] - cen[1], v[2] - cen[2]) / radio;
          w = clamp(w * 1.4) * (1 - suave(0.7, 1.05, dist));
          col = mezclar(col, color, w * 0.94);
          if (w > 0.5) col = mezclar(col, OSCURO, (w - 0.5) * (1 - suave(0, 0.6, dist)) * 1.1);
        } else if (cod === 'fractura') {
          const eje = cf === 'mesial' || cf === 'distal' ? v[2] / (md.fondo / 2) : v[0] / (md.ancho / 2);
          const linea = 0.12 + 0.18 * Math.sin(h * 13) + 0.08 * Math.sin(h * 31);
          const grieta = 1 - suave(0.04, 0.1, Math.abs(eje - linea));
          col = mezclar(col, color, grieta * w * 0.95);
          col = mezclar(col, [0.8, 0.8, 0.82], w * 0.12);
        } else if (cod === 'sellante') {
          col = mezclar(col, color, suave(0.2, 0.6, w) * 0.55);
          if (w > 0.4) mat = MAT.brillo;
        } else {
          const borde = suave(0.25, 0.45, w);
          col = mezclar(col, color, borde * 0.88);
          if (borde > 0.5) mat = MAT.brillo;
        }
      }
    }

    posiciones.set(mundo(v), i * 3);
    normales.set(giro(nn), i * 3);
    colores.set(ausente ? [0.82, 0.86, 0.88] : col, i * 3);
    materiales.set([mat, ao, caras[i]], i * 3);
  }

  let raizMalla: Malla | null = null;
  if (!ausente) {
    const r = raiz(md, implante);
    const rn = haciaAfuera(r.p, normalesSuaves(r.p, r.tri), [0, -md.largoRaiz * 0.4, 0]);
    const k = r.p.length;
    const rp = new Float32Array(k * 3);
    const rnn = new Float32Array(k * 3);
    const rc = new Float32Array(k * 3);
    const rm = new Float32Array(k * 3);
    const colorRaiz: Vec3 = implante ? TITANIO : completo === 'endodoncia' ? mezclar(DENTINA, hex('#c0503a'), 0.55) : DENTINA;
    for (let i = 0; i < k; i++) {
      rp.set(mundo(r.p[i]), i * 3);
      rnn.set(giro(rn[i]), i * 3);
      rc.set(colorRaiz, i * 3);
      rm.set([implante ? MAT.metal : MAT.raiz, 0.85 + 0.15 * clamp(1 + r.p[i][1]), -1], i * 3);
    }
    raizMalla = { posiciones: rp, normales: rnn, colores: rc, materiales: rm, indices: new Uint16Array(r.tri) };
  }

  const marcaCompleta = completo ?? (ausente ? (codigos.has('ausente') ? 'ausente' : 'extraccion_realizada') : null);
  return {
    fdi,
    nombre: nombrePieza(fdi),
    superior: arriba,
    caras,
    posiciones,
    normales,
    colores,
    materiales,
    indices: new Uint16Array(c.tri),
    centro: mundo([0, md.alto * 0.55, 0]),
    radio: Math.max(md.ancho, md.fondo, md.alto) * 0.62,
    ancla: mundo([0, md.alto * 1.22, md.fondo * 0.35]),
    afuera: O,
    ausente,
    movilidad: codigos.has('movilidad'),
    raiz: raizMalla,
    colorMarca: marcaCompleta ? TOOTH_CONDITION_BY_CODE[marcaCompleta]?.color ?? null : null,
  };
}

function catmull(p0: number[], p1: number[], p2: number[], p3: number[], t: number): number[] {
  const t2 = t * t;
  const t3 = t2 * t;
  return p1.map((_, k) =>
    0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2 + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3),
  );
}

function curva(ctrl: number[][], muestras: number): number[][] {
  const out: number[][] = [];
  const tramos = ctrl.length - 1;
  for (let i = 0; i <= muestras; i++) {
    const g = (i / muestras) * tramos;
    const s = Math.min(tramos - 1, Math.floor(g));
    const t = g - s;
    out.push(catmull(ctrl[Math.max(0, s - 1)], ctrl[s], ctrl[s + 1], ctrl[Math.min(tramos, s + 2)], t));
  }
  return out;
}

interface Hueco {
  th: number;
  medio: number;
  cej: number;
  fondo: number;
  papila: number;
}

const ENCIA_FIJA: Vec3 = [0.93, 0.6, 0.61];
const MUCOSA: Vec3 = [0.8, 0.36, 0.42];
const PALADAR: Vec3 = [0.9, 0.56, 0.6];

function encia(rx: number, rz: number, piezas: Hueco[], arriba: boolean): Malla {
  const s = arriba ? 1 : -1;
  const ult = piezas[piezas.length - 1];
  const thMax = ult.th + ult.medio;
  const extra = 0.16;
  const N = 240;
  const P = 34;
  const pos: Vec3[] = [];
  const col: Vec3[] = [];
  const ao: number[] = [];

  const enDiente = (th: number) => {
    const a = Math.abs(th);
    for (let i = 0; i < piezas.length; i++) {
      const pz = piezas[i];
      const lo = pz.th - pz.medio;
      const hi = i + 1 < piezas.length ? (pz.th + piezas[i + 1].th) / 2 : pz.th + pz.medio;
      if (a <= hi || i === piezas.length - 1) {
        const mitad = a < pz.th ? pz.th - lo : hi - pz.th;
        const v = clamp((a - pz.th) / (mitad || 1), -1, 1);
        const vecino = v < 0 ? piezas[Math.max(0, i - 1)] : piezas[Math.min(piezas.length - 1, i + 1)];
        const mezcla = v * v * 0.5;
        return {
          cej: pz.cej + (vecino.cej - pz.cej) * mezcla,
          fondo: pz.fondo + (vecino.fondo - pz.fondo) * mezcla,
          papila: pz.papila * Math.abs(v) ** 2.4,
        };
      }
    }
    return { cej: ult.cej, fondo: ult.fondo, papila: 0 };
  };

  const filas: number[] = [];
  for (let i = 0; i <= N; i++) {
    const th = -(thMax + extra) + (2 * (thMax + extra) * i) / N;
    const a = Math.abs(th);
    const lado = th < 0 ? -1 : 1;
    const mk = puntoArcada(rx, rz, lado, Math.min(a, thMax + extra));
    const d = enDiente(Math.min(a, thMax));
    const e = a > thMax ? (a - thMax) / extra : 0;
    const cierre = Math.sqrt(Math.max(0, 1 - e * e));
    const hb = d.cej - 0.11 + e * 0.55;
    const hm = hb - d.papila * 0.34;
    const f = d.fondo / 2;
    const ctrl = [
      [0, hb + 1.1],
      [-(f + 0.26), hb + 1.0],
      [-(f + 0.32), hb + 0.6],
      [-(f + 0.08), hm + 0.2],
      [-f * 0.84, hm],
      [0, hm + 0.04],
      [f * 0.88, hm],
      [f + 0.12, hm + 0.2],
      [f + 0.28, hb + 0.6],
      [f + 0.24, hb + 1.0],
      [0, hb + 1.1],
    ];
    const perfil = curva(ctrl, P);
    for (const [o, dd] of perfil) {
      const oo = o * cierre;
      const d2 = hb + (dd - hb) * (0.35 + 0.65 * cierre);
      pos.push([mk.centro[0] + mk.vestibular[0] * oo, s * d2, mk.centro[2] + mk.vestibular[2] * oo]);
      const prof = d2 - hm;
      col.push(mezclar(ENCIA_FIJA, MUCOSA, suave(0.45, 1.6, prof)));
      ao.push(0.8 + 0.2 * suave(0, 0.25, prof));
    }
    filas.push(i);
  }
  const ancho = P + 1;
  const tri: number[] = [];
  for (let i = 0; i < N; i++) {
    for (let j = 0; j < P; j++) {
      const a = i * ancho + j;
      const b = a + ancho;
      tri.push(a, b, a + 1, a + 1, b, b + 1);
    }
  }

  if (arriba) {
    const base = pos.length;
    const R = 12;
    const cz = -rz * 0.62;
    const muestras: number[] = [];
    for (let i = 0; i <= N; i += 2) {
      const th = -(thMax + extra) + (2 * (thMax + extra) * i) / N;
      if (Math.abs(th) <= thMax) muestras.push(i);
    }
    const alto = Math.max(...piezas.map((p) => p.cej)) + 0.9;
    for (const i of muestras) {
      const q = pos[i * ancho + 8];
      const d0 = Math.abs(q[1]);
      for (let r = 0; r <= R; r++) {
        const u = r / R;
        const x = q[0] * (1 - u);
        const z = q[2] + (cz - q[2]) * u * 0.12;
        const frente = suave(-1.2, 0.2, z) * (1 - u);
        const d = d0 + (alto - d0) * Math.sin((u * Math.PI) / 2) - 0.05 * Math.sin(u * 22) * frente;
        pos.push([x, d, z]);
        col.push(mezclar(PALADAR, MUCOSA, 0.15 * u));
        ao.push(0.85 + 0.15 * u);
      }
    }
    for (let k = 0; k + 1 < muestras.length; k++) {
      for (let r = 0; r < R; r++) {
        const a = base + k * (R + 1) + r;
        const b = a + R + 1;
        tri.push(a, a + 1, b, a + 1, b + 1, b);
      }
    }
  }

  const nn = normalesSuaves(pos, tri);
  const muestra = Math.floor(N / 2) * ancho + Math.floor(P * 0.85);
  const fuera = punto(nn[muestra], normal([0, 0, 1]));
  const nfin = fuera < 0 ? nn.map((v) => escalar(v, -1)) : nn;
  const posiciones = new Float32Array(pos.length * 3);
  const normales = new Float32Array(pos.length * 3);
  const colores = new Float32Array(pos.length * 3);
  const materiales = new Float32Array(pos.length * 3);
  pos.forEach((p, i) => {
    posiciones.set(p, i * 3);
    normales.set(nfin[i], i * 3);
    colores.set(col[i], i * 3);
    materiales.set([MAT.encia, ao[i], -1], i * 3);
  });
  return { posiciones, normales, colores, materiales, indices: new Uint16Array(tri) };
}

const DISTANCIA = 0.04;

export function armarBoca(hallazgos: Hallazgo[], denticion: 'permanent' | 'temporary'): Boca {
  const porPieza = new Map<string, Hallazgo[]>();
  for (const h of hallazgos) {
    if (!porPieza.has(h.fdi_number)) porPieza.set(h.fdi_number, []);
    porPieza.get(h.fdi_number)!.push(h);
  }
  const temporal = denticion === 'temporary';
  const piezas: Pieza[] = [];
  const encias: (Malla & { superior: boolean })[] = [];
  const arcos = temporal
    ? [
        { cuadrantes: [5, 6], arriba: true, medidas: TEMPORAL, rx: 2.0, rz: 2.25 },
        { cuadrantes: [8, 7], arriba: false, medidas: TEMPORAL, rx: 1.85, rz: 2.05 },
      ]
    : [
        { cuadrantes: [1, 2], arriba: true, medidas: SUPERIOR, rx: 2.62, rz: 3.1 },
        { cuadrantes: [4, 3], arriba: false, medidas: INFERIOR, rx: 2.4, rz: 2.86 },
      ];

  for (const arco of arcos) {
    const lugares = ubicar(arco.medidas, arco.rx, arco.rz);
    const huecos: Hueco[] = lugares.map((l, i) => ({
      th: l.th,
      medio: l.medio,
      cej: DISTANCIA + arco.medidas[i].alto,
      fondo: arco.medidas[i].fondo,
      papila: arco.medidas[i].tipo === 'molar' ? 0.7 : arco.medidas[i].tipo === 'premolar' ? 0.85 : 1,
    }));
    arco.cuadrantes.forEach((q, k) => {
      const lado = k === 0 ? -1 : 1;
      lugares.forEach(({ th }, i) => {
        const fdi = `${q}${i + 1}`;
        piezas.push(
          armarPieza(fdi, arco.medidas[i], puntoArcada(arco.rx, arco.rz, lado, th), arco.arriba, DISTANCIA, porPieza.get(fdi) ?? []),
        );
      });
    });
    encias.push({ ...encia(arco.rx, arco.rz, huecos, arco.arriba), superior: arco.arriba });
  }
  return { piezas, encias };
}

export function describirPieza(hallazgos: Hallazgo[], fdi: string): { etiqueta: string; color: string; cara: string; superficie: string }[] {
  const caras: Record<string, string> = {
    whole: 'Diente completo',
    mesial: 'Mesial',
    distal: 'Distal',
    vestibular: 'Vestibular',
    lingual: 'Lingual/Palatina',
    oclusal: 'Oclusal/Incisal',
  };
  return hallazgos
    .filter((h) => h.fdi_number === fdi && h.condition !== 'sano')
    .map((h) => ({
      etiqueta: TOOTH_CONDITION_BY_CODE[h.condition]?.label ?? h.condition,
      color: TOOTH_CONDITION_BY_CODE[h.condition]?.color ?? '#999',
      cara: caras[h.surface] ?? h.surface,
      superficie: h.surface,
    }));
}

export function colorPrincipal(hallazgos: Hallazgo[], fdi: string): string | null {
  const aqui = hallazgos.filter((h) => h.fdi_number === fdi && h.condition !== 'sano');
  const orden = ['ausente', 'extraccion_realizada', ...COMPLETOS, ...ORDEN_CARA];
  const top = orden.find((c) => aqui.some((h) => h.condition === c));
  return top ? TOOTH_CONDITION_BY_CODE[top]?.color ?? null : null;
}

export const ORDEN_PIEZAS = {
  permanent: {
    superior: ['18', '17', '16', '15', '14', '13', '12', '11', '21', '22', '23', '24', '25', '26', '27', '28'],
    inferior: ['48', '47', '46', '45', '44', '43', '42', '41', '31', '32', '33', '34', '35', '36', '37', '38'],
  },
  temporary: {
    superior: ['55', '54', '53', '52', '51', '61', '62', '63', '64', '65'],
    inferior: ['85', '84', '83', '82', '81', '71', '72', '73', '74', '75'],
  },
};
