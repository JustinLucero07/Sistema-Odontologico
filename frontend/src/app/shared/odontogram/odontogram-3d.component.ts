import {
  AfterViewInit,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  NgZone,
  OnChanges,
  OnDestroy,
  Output,
  ViewChild,
  computed,
  inject,
  signal,
} from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  Boca,
  CARAS,
  Cara,
  Hallazgo,
  Malla,
  ORDEN_PIEZAS,
  Pieza,
  Vec3,
  armarBoca,
  colorPrincipal,
  describirPieza,
  nombrePieza,
} from './dental-3d';
import { SURFACE_LABELS, TOOTH_CONDITION_BY_CODE } from './tooth-conditions';

type M4 = Float32Array;
type Vista = 'frente' | 'arriba' | 'abajo' | 'derecha' | 'izquierda';

function perspectiva(fov: number, aspecto: number, cerca: number, lejos: number): M4 {
  const f = 1 / Math.tan(fov / 2);
  const nf = 1 / (cerca - lejos);
  return new Float32Array([f / aspecto, 0, 0, 0, 0, f, 0, 0, 0, 0, (lejos + cerca) * nf, -1, 0, 0, 2 * lejos * cerca * nf, 0]);
}

function mirarA(ojo: Vec3, centro: Vec3, arriba: Vec3): M4 {
  const z = norm([ojo[0] - centro[0], ojo[1] - centro[1], ojo[2] - centro[2]]);
  const x = norm(cruz(arriba, z));
  const y = cruz(z, x);
  return new Float32Array([
    x[0], y[0], z[0], 0,
    x[1], y[1], z[1], 0,
    x[2], y[2], z[2], 0,
    -punto(x, ojo), -punto(y, ojo), -punto(z, ojo), 1,
  ]);
}

function mult(a: M4, b: M4): M4 {
  const o = new Float32Array(16);
  for (let c = 0; c < 4; c++) {
    for (let r = 0; r < 4; r++) {
      let s = 0;
      for (let k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k];
      o[c * 4 + r] = s;
    }
  }
  return o;
}

const cruz = (a: Vec3, b: Vec3): Vec3 => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const punto = (a: Vec3, b: Vec3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const resta = (a: Vec3, b: Vec3): Vec3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
function norm(a: Vec3): Vec3 {
  const l = Math.hypot(a[0], a[1], a[2]) || 1;
  return [a[0] / l, a[1] / l, a[2] / l];
}

const VERTICES = `
attribute vec3 aPos; attribute vec3 aNor; attribute vec3 aCol; attribute vec3 aMat;
uniform mat4 uMvp; uniform vec3 uOff;
varying vec3 vNor; varying vec3 vCol; varying vec3 vPos; varying vec3 vMat;
void main() {
  vec3 p = aPos + uOff;
  vNor = aNor; vCol = aCol; vPos = p; vMat = aMat;
  gl_Position = uMvp * vec4(p, 1.0);
}`;

const FRAGMENTOS = `
precision highp float;
varying vec3 vNor; varying vec3 vCol; varying vec3 vPos; varying vec3 vMat;
uniform vec3 uOjo; uniform float uAlfa; uniform vec3 uRim; uniform float uRimFuerza;
uniform float uCara; uniform vec3 uCaraColor;
float hash(vec3 p) { p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float ruido(vec3 x) {
  vec3 i = floor(x); vec3 f = fract(x); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(hash(i), hash(i + vec3(1,0,0)), f.x), mix(hash(i + vec3(0,1,0)), hash(i + vec3(1,1,0)), f.x), f.y),
             mix(mix(hash(i + vec3(0,0,1)), hash(i + vec3(1,0,1)), f.x), mix(hash(i + vec3(0,1,1)), hash(i + vec3(1,1,1)), f.x), f.y), f.z);
}
void main() {
  vec3 n = normalize(vNor);
  vec3 v = normalize(uOjo - vPos);
  if (dot(n, v) < 0.0) n = -n;
  float tipo = vMat.x;
  float ao = vMat.y;
  vec3 base = pow(vCol, vec3(2.2));
  bool encia = tipo > 0.5 && tipo < 1.5;
  bool metal = tipo > 1.5 && tipo < 2.5;
  bool raiz = tipo > 2.5 && tipo < 3.5;
  bool brillo = tipo > 3.5;
  if (encia) {
    float st = ruido(vPos * 34.0);
    base *= 0.92 + 0.12 * st;
    n = normalize(n + (vec3(ruido(vPos * 42.0 + 3.1), ruido(vPos * 42.0 + 7.7), ruido(vPos * 42.0 + 1.3)) - 0.5) * 0.18);
  }
  vec3 L1 = normalize(vec3(0.35, 0.85, 0.8));
  vec3 L2 = normalize(vec3(-0.85, 0.15, 0.45));
  vec3 L3 = normalize(vec3(0.1, -0.6, 0.6));
  float wrap = encia ? 0.55 : (metal ? 0.1 : 0.32);
  float d1 = max((dot(n, L1) + wrap) / (1.0 + wrap), 0.0);
  float d2 = max((dot(n, L2) + wrap) / (1.0 + wrap), 0.0);
  float d3 = max((dot(n, L3) + wrap) / (1.0 + wrap), 0.0);
  float dv = max(dot(n, v), 0.0);
  vec3 luz = vec3(1.0, 0.96, 0.9) * d1 * 1.05 + vec3(0.62, 0.72, 0.9) * d2 * 0.45 + vec3(0.9, 0.8, 0.75) * d3 * 0.22 + vec3(1.0) * dv * 0.3;
  vec3 amb = mix(vec3(0.16, 0.14, 0.14), vec3(0.3, 0.33, 0.37), n.y * 0.5 + 0.5);
  float gloss = encia ? 48.0 : metal ? 120.0 : raiz ? 16.0 : brillo ? 180.0 : 85.0;
  float fuerza = encia ? 0.35 : metal ? 1.4 : raiz ? 0.05 : brillo ? 1.0 : 0.6;
  float fres = 0.04 + 0.96 * pow(1.0 - dv, 5.0);
  vec3 h1 = normalize(L1 + v);
  vec3 h2 = normalize(L2 + v);
  float sp = pow(max(dot(n, h1), 0.0), gloss) + 0.45 * pow(max(dot(n, h2), 0.0), gloss) + 0.25 * pow(max(dot(n, v), 0.0), gloss * 1.5);
  vec3 colEsp = metal ? base * 1.4 + 0.1 : vec3(1.0);
  vec3 col = base * (luz + amb) * ao + colEsp * sp * fuerza * (0.55 + fres);
  if (tipo < 0.5) col += base * vec3(1.0, 0.82, 0.68) * pow(1.0 - dv, 2.5) * 0.14;
  if (metal) {
    vec3 r = reflect(-v, n);
    col += base * (0.25 + 0.75 * smoothstep(-0.3, 0.9, r.y)) * 0.55;
  }
  if (uCara >= 0.0 && abs(vMat.z - uCara) < 0.5) {
    col = mix(col, pow(uCaraColor, vec3(2.2)), 0.5);
  }
  col += pow(uRim, vec3(2.2)) * pow(1.0 - dv, 2.0) * uRimFuerza;
  col = (col * (2.51 * col + 0.03)) / (col * (2.43 * col + 0.59) + 0.14);
  col = pow(clamp(col, 0.0, 1.0), vec3(1.0 / 2.2));
  gl_FragColor = vec4(col, uAlfa);
}`;

interface Buffers {
  pos: WebGLBuffer;
  nor: WebGLBuffer;
  col: WebGLBuffer;
  mat: WebGLBuffer;
  idx: WebGLBuffer;
  n: number;
}

interface Camara {
  yaw: number;
  pitch: number;
  dist: number;
  mira: Vec3;
}

const INICIO: Camara = { yaw: 0, pitch: 0.16, dist: 12.4, mira: [0, 0, -1.45] };

@Component({
  selector: 'app-odontogram-3d',
  standalone: true,
  imports: [MatIconModule, MatTooltipModule],
  template: `
    <div class="visor" [class.completa]="completa()">
      <div class="escena" #escena>
        <canvas
          #lienzo
          tabindex="0"
          aria-label="Boca en 3D. Arrastre para girar, use las flechas del teclado o los botones de vistas."
          (pointerdown)="bajar($event)"
          (pointermove)="mover($event)"
          (pointerup)="subir($event)"
          (pointercancel)="subir($event)"
          (pointerleave)="salir()"
          (wheel)="rueda($event)"
          (dblclick)="dobleClic($event)"
          (keydown)="tecla($event)"
        ></canvas>
        @if (!soportado()) {
          <p class="aviso">Este navegador no puede dibujar en 3D. Use el odontograma 2D.</p>
        }

        <div class="numeros" [class.visibles]="numeros()">
          @for (e of etiquetas(); track e.fdi) {
            <button
              type="button"
              class="num"
              [attr.data-fdi]="e.fdi"
              [class.sel]="e.fdi === elegida()"
              [class.hov]="e.fdi === hoverFdi()"
              [class.marcada]="!!e.color"
              [class.ausente]="e.ausente"
              [style.--c]="e.color ?? 'transparent'"
              (click)="elegir(e.fdi)"
              [attr.aria-label]="'Pieza ' + e.fdi"
            >{{ e.fdi }}</button>
          }
        </div>

        <div class="tip" #tip [class.on]="!!hover()">
          @if (hover(); as h) {
            <strong>{{ h.fdi }} · {{ h.nombre }}</strong>
            @if (editable && pincel && h.cara) {
              <span class="pincel"><i [style.background]="pincel.color"></i>Clic: {{ pincel.label }} en {{ caraTexto(h.cara) }}</span>
            } @else if (editable && h.cara) {
              <span>Clic para registrar en {{ caraTexto(h.cara) }}</span>
            } @else {
              <span>{{ h.resumen }}</span>
            }
          }
        </div>

        <div class="barra arriba-izq">
          <div class="seg" role="group" aria-label="Arcada">
            @for (a of arcadas; track a[0]) {
              <button type="button" [class.on]="arcada() === a[0]" (click)="arcada.set(a[0])">{{ a[1] }}</button>
            }
          </div>
        </div>

        <div class="barra arriba-der">
          <div class="grupo" role="group" aria-label="Vistas">
            @for (v of vistas; track v[0]) {
              <button type="button" class="ico" [class.on]="vistaActual() === v[0]" (click)="vista(v[0])" [matTooltip]="v[1]" [attr.aria-label]="v[1]">
                <mat-icon [style.transform]="v[3]">{{ v[2] }}</mat-icon>
              </button>
            }
          </div>
          <div class="grupo">
            <button type="button" class="ico" [class.on]="numeros()" (click)="numeros.set(!numeros())" matTooltip="Números de pieza" aria-label="Números de pieza">
              <mat-icon>pin</mat-icon>
            </button>
            <button type="button" class="ico" [class.on]="raices()" (click)="raices.set(!raices())" matTooltip="Ver raíces e implantes" aria-label="Ver raíces">
              <mat-icon>layers</mat-icon>
            </button>
            <button type="button" class="ico" [class.on]="girando()" (click)="girando.set(!girando())" [matTooltip]="girando() ? 'Detener giro' : 'Girar solo'" aria-label="Girar solo">
              <mat-icon>360</mat-icon>
            </button>
            <button type="button" class="ico" (click)="restablecer()" matTooltip="Volver a la vista inicial" aria-label="Vista inicial">
              <mat-icon>restart_alt</mat-icon>
            </button>
            <button type="button" class="ico" (click)="pantallaCompleta()" [matTooltip]="completa() ? 'Salir de pantalla completa' : 'Pantalla completa (para enseñar al paciente)'" aria-label="Pantalla completa">
              <mat-icon>{{ completa() ? 'fullscreen_exit' : 'fullscreen' }}</mat-icon>
            </button>
          </div>
        </div>

        <label class="barra abajo-izq apertura">
          <mat-icon>unfold_more</mat-icon>
          <span>Abrir</span>
          <input type="range" min="0" max="1" step="0.01" [value]="aperturaObjetivo" (input)="abrir(+$any($event.target).value)" aria-label="Abrir la boca" />
        </label>

        @if (elegida(); as fdi) {
          <aside class="detalle" aria-live="polite">
            <header>
              <div>
                <strong>Pieza {{ fdi }}</strong>
                <span>{{ nombre(fdi) }}</span>
              </div>
              <button type="button" class="cerrar" (click)="elegir(null)" aria-label="Cerrar"><mat-icon>close</mat-icon></button>
            </header>

            <div class="esquema">
              <svg viewBox="0 0 100 100" role="img" [attr.aria-label]="'Caras de la pieza ' + fdi">
                @for (f of figuras(fdi); track f.cara) {
                  <polygon
                    [attr.points]="f.puntos"
                    [attr.fill]="f.color ?? 'var(--cara-vacia)'"
                    [class.activa]="editable"
                    (click)="tocarCara(fdi, f.cara)"
                    (pointerenter)="caraEsquema.set(f.cara)"
                    (pointerleave)="caraEsquema.set(null)"
                  >
                    <title>{{ caraTexto(f.cara) }}</title>
                  </polygon>
                  <text [attr.x]="f.tx" [attr.y]="f.ty">{{ f.letra }}</text>
                }
              </svg>
              <div class="esquema-txt">
                @if (editable) {
                  <span>{{ caraEsquema() ? caraTexto(caraEsquema()!) : 'Toque una cara para registrar' }}</span>
                  <button type="button" class="completo" (click)="tocarCara(fdi, 'whole')">Diente completo</button>
                } @else {
                  <span>{{ detalle().length ? detalle().length + (detalle().length === 1 ? ' hallazgo' : ' hallazgos') : 'Sana' }}</span>
                }
              </div>
            </div>

            @if (detalle().length === 0) {
              <p class="sano"><mat-icon>check_circle</mat-icon>Sin hallazgos registrados.</p>
            } @else {
              <ul>
                @for (d of detalle(); track $index) {
                  <li><i [style.background]="d.color"></i><b>{{ d.etiqueta }}</b><span>{{ d.cara }}</span></li>
                }
              </ul>
            }
            <button type="button" class="enfocar" (click)="enfocar(fdi)"><mat-icon>center_focus_strong</mat-icon>Acercar a esta pieza</button>
          </aside>
        }

        <p class="ayuda">{{ ayuda() }}</p>
      </div>

      <div class="mapa">
        @for (fila of filas(); track $index) {
          <div class="fila">
            @for (f of fila; track f.fdi; let i = $index) {
              @if (i === fila.length / 2) { <span class="linea-media"></span> }
              <button
                type="button"
                class="pza"
                [class.sel]="f.fdi === elegida()"
                [class.ausente]="f.ausente"
                [style.--c]="f.color ?? 'transparent'"
                (click)="elegir(f.fdi); enfocar(f.fdi)"
                (pointerenter)="hoverMapa(f.fdi)"
                (pointerleave)="hoverMapa(null)"
                [attr.aria-label]="'Pieza ' + f.fdi"
              >
                {{ f.fdi }}
                @if (f.color) { <i></i> }
              </button>
            }
          </div>
        }
        @if (leyenda().length) {
          <div class="leyenda">
            @for (l of leyenda(); track l.label) {
              <span><i [style.background]="l.color"></i>{{ l.label }} <b>{{ l.n }}</b></span>
            }
          </div>
        }
      </div>
    </div>
  `,
  styles: [
    `
      :host { display: block; --cara-vacia: #f4f1ea; }
      .visor { display: grid; gap: 10px; }
      .escena { position: relative; height: 580px; border-radius: var(--radius-lg, 20px); overflow: hidden; color: #fff;
        background: radial-gradient(110% 80% at 50% 38%, #2b3e42 0%, #172427 55%, #0e1719 100%); }
      .escena::after { content: ''; position: absolute; left: 18%; right: 18%; bottom: 7%; height: 12%; pointer-events: none;
        background: radial-gradient(closest-side, rgba(0,0,0,.35), transparent); filter: blur(6px); }
      .visor.completa .escena { height: 100vh; border-radius: 0; }
      canvas { display: block; width: 100%; height: 100%; touch-action: none; cursor: grab; outline: none; position: relative; z-index: 1; }
      canvas:active { cursor: grabbing; }
      canvas:focus-visible { box-shadow: inset 0 0 0 2px rgba(120, 220, 205, .7); }
      .aviso { position: absolute; inset: 0; display: grid; place-items: center; margin: 0; z-index: 2; }

      .barra { position: absolute; z-index: 3; display: flex; gap: 8px; align-items: center; }
      .arriba-izq { top: 12px; left: 12px; }
      .arriba-der { top: 12px; right: 12px; }
      .abajo-izq { bottom: 12px; left: 12px; }
      .seg, .grupo { display: flex; gap: 2px; padding: 3px; border-radius: 999px; background: rgba(255,255,255,.09);
        backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,.08); }
      .seg button { border: 0; border-radius: 999px; padding: 6px 13px; background: transparent; color: rgba(255,255,255,.78);
        font: inherit; font-size: .78rem; font-weight: 600; cursor: pointer; transition: background .15s ease, color .15s ease; }
      .seg button.on { background: #fff; color: #14242b; }
      .ico { display: grid; place-items: center; width: 34px; height: 34px; border: 0; border-radius: 999px; background: transparent;
        color: rgba(255,255,255,.82); cursor: pointer; transition: background .15s ease, color .15s ease, transform .12s ease;
        mat-icon { font-size: 19px; width: 19px; height: 19px; } }
      .ico:hover { background: rgba(255,255,255,.12); color: #fff; }
      .ico:active { transform: scale(.92); }
      .ico.on { background: rgba(120, 220, 205, .22); color: #8ff0de; }
      .apertura { gap: 8px; padding: 6px 14px 6px 10px; border-radius: 999px; background: rgba(255,255,255,.09); backdrop-filter: blur(12px);
        font-size: .76rem; color: rgba(255,255,255,.8); cursor: pointer;
        mat-icon { font-size: 18px; width: 18px; height: 18px; }
        input { width: 120px; accent-color: #8ff0de; cursor: pointer; } }

      .numeros { position: absolute; inset: 0; z-index: 2; pointer-events: none; }
      .num { position: absolute; left: 0; top: 0; pointer-events: none; opacity: 0; border: 0; padding: 2px 6px; border-radius: 999px;
        font: inherit; font-size: .68rem; font-weight: 700; line-height: 1.3; color: #14242b; background: rgba(255,255,255,.88);
        box-shadow: 0 0 0 2px var(--c), 0 4px 10px -4px rgba(0,0,0,.6); will-change: transform, opacity; transition: background .15s ease; }
      .numeros.visibles .num, .num.sel, .num.hov { pointer-events: auto; cursor: pointer; }
      .num.marcada { background: #fff; }
      .num.ausente { background: rgba(255,255,255,.5); text-decoration: line-through; }
      .num.sel { background: #8ff0de; }

      .tip { position: absolute; left: 0; top: 0; z-index: 4; pointer-events: none; opacity: 0; display: grid; gap: 2px; max-width: 260px;
        padding: 8px 11px; border-radius: 12px; background: rgba(12, 22, 24, .86); backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,.1); font-size: .76rem; color: rgba(255,255,255,.8); transition: opacity .12s ease;
        strong { color: #fff; font-size: .8rem; }
        .pincel { display: inline-flex; align-items: center; gap: 6px; color: #fff; }
        i { width: 9px; height: 9px; border-radius: 3px; } }
      .tip.on { opacity: 1; }

      .detalle { position: absolute; z-index: 3; right: 12px; top: 60px; width: 270px; max-height: calc(100% - 120px); overflow-y: auto;
        padding: 12px 14px; border-radius: 18px; background: rgba(255,255,255,.96); color: var(--color-ink, #14242b);
        box-shadow: 0 24px 50px -22px rgba(0,0,0,.7); animation: entra .22s cubic-bezier(.2,.9,.3,1);
        header { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px;
          strong { display: block; font-size: 1.02rem; } span { display: block; font-size: .76rem; color: #5f6f72; } }
        ul { list-style: none; margin: 10px 0 0; padding: 0; display: grid; gap: 6px; font-size: .82rem; }
        li { display: grid; grid-template-columns: 10px 1fr; column-gap: 8px; align-items: center;
          b { font-weight: 600; } span { grid-column: 2; color: #6b7b7e; font-size: .74rem; } }
        li i { width: 10px; height: 10px; border-radius: 3px; } }
      .cerrar { border: 0; background: transparent; cursor: pointer; color: #5f6f72; display: grid; place-items: center; padding: 2px; border-radius: 8px;
        &:hover { background: #eef2f2; } }
      .esquema { display: flex; gap: 12px; align-items: center; margin-top: 10px;
        svg { width: 92px; height: 92px; flex-shrink: 0; }
        polygon { stroke: #9aa9ac; stroke-width: 1.2; transition: filter .12s ease; }
        polygon.activa { cursor: pointer; }
        polygon.activa:hover { filter: brightness(.9); stroke: #0d7f76; stroke-width: 2; }
        text { font-size: 9px; font-weight: 700; fill: #5f6f72; pointer-events: none; text-anchor: middle; dominant-baseline: middle; } }
      .esquema-txt { display: grid; gap: 8px; font-size: .76rem; color: #5f6f72; }
      .completo { border: 1px solid #c9d4d5; background: #fff; border-radius: 999px; padding: 5px 10px; font: inherit; font-size: .74rem;
        font-weight: 600; color: #14242b; cursor: pointer; &:hover { border-color: #0d7f76; color: #0d7f76; } }
      .sano { display: flex; align-items: center; gap: 6px; margin: 10px 0 0; font-size: .82rem; color: #2b9a5b;
        mat-icon { font-size: 18px; width: 18px; height: 18px; } }
      .enfocar { display: flex; align-items: center; justify-content: center; gap: 6px; width: 100%; margin-top: 12px; padding: 8px;
        border: 0; border-radius: 12px; background: #eef4f3; color: #0d6d66; font: inherit; font-size: .8rem; font-weight: 600; cursor: pointer;
        mat-icon { font-size: 18px; width: 18px; height: 18px; }
        &:hover { background: #e0eeec; } }
      .ayuda { position: absolute; z-index: 2; right: 14px; bottom: 16px; max-width: 46%; margin: 0; text-align: right; pointer-events: none;
        font-size: .72rem; color: rgba(255,255,255,.55); }

      .mapa { display: grid; gap: 6px; justify-items: center; padding: 10px 8px; border-radius: var(--radius-md, 14px);
        background: var(--color-surface-muted, #f3f1ec); overflow-x: auto; }
      .fila { display: flex; gap: 3px; align-items: center; }
      .linea-media { width: 1px; height: 22px; margin: 0 5px; background: var(--color-border-strong, #c9cfcf); }
      .pza { position: relative; min-width: 34px; padding: 4px 0 6px; border: 1px solid transparent; border-radius: 9px; background: var(--color-surface, #fff);
        font: inherit; font-size: .74rem; font-weight: 700; color: var(--color-ink-soft, #3d4f53); cursor: pointer;
        transition: border-color .12s ease, transform .12s ease, background .12s ease;
        i { position: absolute; left: 50%; bottom: 2px; width: 14px; height: 3px; margin-left: -7px; border-radius: 2px; background: var(--c); } }
      .pza:hover { border-color: var(--color-primary, #0d7f76); transform: translateY(-1px); }
      .pza.sel { background: var(--color-primary, #0d7f76); color: #fff; }
      .pza.ausente { opacity: .45; text-decoration: line-through; }
      .leyenda { display: flex; flex-wrap: wrap; justify-content: center; gap: 4px 14px; margin-top: 2px; font-size: .74rem; color: var(--color-ink-soft, #3d4f53);
        span { display: inline-flex; align-items: center; gap: 6px; } i { width: 10px; height: 10px; border-radius: 3px; }
        b { color: var(--color-ink-faint, #7b8a8d); font-weight: 600; } }

      @keyframes entra { from { opacity: 0; transform: translateY(-6px) scale(.98); } }
      @media (max-width: 700px) {
        .escena { height: 460px; }
        .arriba-der { top: 56px; left: 8px; right: 8px; justify-content: space-between; gap: 4px; }
        .grupo { gap: 0; padding: 2px; }
        .ico { width: 30px; height: 30px; mat-icon { font-size: 17px; width: 17px; height: 17px; } }
        .apertura input { width: 90px; }
        .detalle { top: auto; bottom: 56px; left: 10px; right: 10px; width: auto; max-height: 55%; }
        .mapa { justify-items: start; }
        .ayuda { display: none; }
      }
      @media (prefers-reduced-motion: reduce) { .detalle { animation: none; } }
    `,
  ],
})
export class Odontogram3dComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input() conditions: Hallazgo[] = [];
  @Input() denture: 'permanent' | 'temporary' = 'permanent';
  @Input() selectedFdi: string | null = null;
  @Input() editable = false;
  @Input() pincel: { label: string; color: string } | null = null;
  @Output() toothSelected = new EventEmitter<string | null>();
  @Output() surfaceClicked = new EventEmitter<{ fdi: string; surface: Cara | 'whole' }>();

  @ViewChild('lienzo') private lienzoRef!: ElementRef<HTMLCanvasElement>;
  @ViewChild('escena') private escenaRef!: ElementRef<HTMLDivElement>;
  @ViewChild('tip') private tipRef!: ElementRef<HTMLDivElement>;
  private readonly zone = inject(NgZone);
  private readonly sinMovimiento = typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;

  readonly soportado = signal(true);
  readonly girando = signal(false);
  readonly completa = signal(false);
  readonly numeros = signal(true);
  readonly raices = signal(false);
  readonly elegida = signal<string | null>(null);
  readonly hoverFdi = signal<string | null>(null);
  readonly hover = signal<{ fdi: string; nombre: string; cara: Cara | null; resumen: string } | null>(null);
  readonly caraEsquema = signal<Cara | null>(null);
  readonly arcada = signal<'ambas' | 'superior' | 'inferior'>('ambas');
  readonly vistaActual = signal<Vista | null>('frente');
  readonly detalle = signal<{ etiqueta: string; color: string; cara: string; superficie: string }[]>([]);
  readonly hallazgos = signal<Hallazgo[]>([]);
  readonly denticion = signal<'permanent' | 'temporary'>('permanent');
  readonly arcadas: ['ambas' | 'superior' | 'inferior', string][] = [['ambas', 'Ambas'], ['superior', 'Maxilar'], ['inferior', 'Mandíbula']];
  readonly vistas: [Vista, string, string, string][] = [
    ['frente', 'Frente', 'face', ''],
    ['derecha', 'Lado derecho del paciente', 'switch_left', ''],
    ['izquierda', 'Lado izquierdo del paciente', 'switch_right', ''],
    ['arriba', 'Oclusal superior', 'expand_less', ''],
    ['abajo', 'Oclusal inferior', 'expand_more', ''],
  ];

  readonly etiquetas = computed(() => {
    const hs = this.hallazgos();
    const orden = ORDEN_PIEZAS[this.denticion()];
    return [...orden.superior, ...orden.inferior].map((fdi) => ({
      fdi,
      color: colorPrincipal(hs, fdi),
      ausente: hs.some((h) => h.fdi_number === fdi && (h.condition === 'ausente' || h.condition === 'extraccion_realizada')),
    }));
  });

  readonly filas = computed(() => {
    const porFdi = new Map(this.etiquetas().map((e) => [e.fdi, e]));
    const orden = ORDEN_PIEZAS[this.denticion()];
    return [orden.superior, orden.inferior].map((f) => f.map((fdi) => porFdi.get(fdi)!));
  });

  readonly leyenda = computed(() => {
    const cuenta = new Map<string, Set<string>>();
    for (const h of this.hallazgos()) {
      if (h.condition === 'sano') continue;
      if (!cuenta.has(h.condition)) cuenta.set(h.condition, new Set());
      cuenta.get(h.condition)!.add(h.fdi_number);
    }
    return [...cuenta.entries()].map(([c, piezas]) => ({
      label: TOOTH_CONDITION_BY_CODE[c]?.label ?? c,
      color: TOOTH_CONDITION_BY_CODE[c]?.color ?? '#999',
      n: piezas.size,
    }));
  });

  readonly ayuda = computed(() =>
    this.editable
      ? 'Arrastre para girar · doble clic para acercar · pase el mouse para ver la cara y toque para registrar'
      : 'Arrastre para girar · rueda o pellizco para acercar · doble clic en una pieza para verla de cerca',
  );

  aperturaObjetivo = 0.42;
  private apertura = 0.42;

  private gl: WebGLRenderingContext | null = null;
  private prog: WebGLProgram | null = null;
  private loc: Record<string, WebGLUniformLocation | null> = {};
  private atr: Record<string, number> = {};
  private boca: Boca | null = null;
  private piezas: { pieza: Pieza; buf: Buffers; raiz: Buffers | null }[] = [];
  private encias: { superior: boolean; buf: Buffers }[] = [];
  private cuadro = 0;
  private observador: ResizeObserver | null = null;
  private etiquetasDom = new Map<string, HTMLElement>();
  private ultimo = performance.now();

  private cam: Camara = this.sinMovimiento ? { ...INICIO } : { yaw: -0.85, pitch: 0.42, dist: 17, mira: [...INICIO.mira] as Vec3 };
  private destino: Camara = { ...INICIO, mira: [...INICIO.mira] as Vec3 };
  private vel = { yaw: 0, pitch: 0 };
  private punteros = new Map<number, { x: number; y: number }>();
  private arrastre = { x: 0, y: 0, movido: 0, activo: false };
  private pellizco = 0;
  private sobre: { x: number; y: number } | null = null;
  private pendienteHover = false;
  private hoverCara: Cara | null = null;
  private mapaHover: string | null = null;

  ngAfterViewInit(): void {
    const canvas = this.lienzoRef.nativeElement;
    const gl = canvas.getContext('webgl', { antialias: true, alpha: true, premultipliedAlpha: false });
    if (!gl) {
      this.soportado.set(false);
      return;
    }
    this.gl = gl;
    this.prog = this.programa(gl);
    for (const u of ['uMvp', 'uOff', 'uOjo', 'uAlfa', 'uRim', 'uRimFuerza', 'uCara', 'uCaraColor']) this.loc[u] = gl.getUniformLocation(this.prog, u);
    for (const a of ['aPos', 'aNor', 'aCol', 'aMat']) this.atr[a] = gl.getAttribLocation(this.prog, a);
    this.reconstruir();
    this.observador = new ResizeObserver(() => this.ajustar());
    this.observador.observe(canvas);
    this.ajustar();
    this.zone.runOutsideAngular(() => this.bucle());
    document.addEventListener('fullscreenchange', this.alCambiarPantalla);
  }

  ngOnChanges(): void {
    this.hallazgos.set(this.conditions ?? []);
    this.denticion.set(this.denture);
    if (this.gl) this.reconstruir();
    if (this.selectedFdi !== this.elegida()) this.elegir(this.selectedFdi, false);
    else if (this.elegida()) this.detalle.set(describirPieza(this.conditions ?? [], this.elegida()!));
  }

  ngOnDestroy(): void {
    cancelAnimationFrame(this.cuadro);
    this.observador?.disconnect();
    document.removeEventListener('fullscreenchange', this.alCambiarPantalla);
    if (this.gl) this.liberarTodo(this.gl);
  }

  private programa(gl: WebGLRenderingContext): WebGLProgram {
    const sh = (tipo: number, src: string) => {
      const s = gl.createShader(tipo)!;
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) console.error(gl.getShaderInfoLog(s));
      return s;
    };
    const p = gl.createProgram()!;
    gl.attachShader(p, sh(gl.VERTEX_SHADER, VERTICES));
    gl.attachShader(p, sh(gl.FRAGMENT_SHADER, FRAGMENTOS));
    gl.linkProgram(p);
    return p;
  }

  private subir3D(gl: WebGLRenderingContext, m: Malla): Buffers {
    const buf = (datos: ArrayBufferView, tipo: number) => {
      const b = gl.createBuffer()!;
      gl.bindBuffer(tipo, b);
      gl.bufferData(tipo, datos, gl.STATIC_DRAW);
      return b;
    };
    return {
      pos: buf(m.posiciones, gl.ARRAY_BUFFER),
      nor: buf(m.normales, gl.ARRAY_BUFFER),
      col: buf(m.colores, gl.ARRAY_BUFFER),
      mat: buf(m.materiales, gl.ARRAY_BUFFER),
      idx: buf(m.indices, gl.ELEMENT_ARRAY_BUFFER),
      n: m.indices.length,
    };
  }

  private liberar(gl: WebGLRenderingContext, b: Buffers): void {
    for (const x of [b.pos, b.nor, b.col, b.mat, b.idx]) gl.deleteBuffer(x);
  }

  private liberarTodo(gl: WebGLRenderingContext): void {
    for (const p of this.piezas) {
      this.liberar(gl, p.buf);
      if (p.raiz) this.liberar(gl, p.raiz);
    }
    for (const e of this.encias) this.liberar(gl, e.buf);
  }

  private reconstruir(): void {
    const gl = this.gl;
    if (!gl) return;
    this.liberarTodo(gl);
    this.boca = armarBoca(this.conditions ?? [], this.denture);
    this.piezas = this.boca.piezas.map((pieza) => ({
      pieza,
      buf: this.subir3D(gl, pieza),
      raiz: pieza.raiz ? this.subir3D(gl, pieza.raiz) : null,
    }));
    this.encias = this.boca.encias.map((e) => ({ superior: e.superior, buf: this.subir3D(gl, e) }));
    this.etiquetasDom.clear();
  }

  private ajustar(): void {
    const c = this.lienzoRef?.nativeElement;
    if (!c) return;
    const r = Math.min(window.devicePixelRatio || 1, 2);
    c.width = Math.max(1, Math.round(c.clientWidth * r));
    c.height = Math.max(1, Math.round(c.clientHeight * r));
    this.aspecto = c.clientWidth / Math.max(1, c.clientHeight);
  }

  private aspecto = 1.6;

  private ojo(cam = this.cam): Vec3 {
    const cp = Math.cos(cam.pitch);
    const d = cam.dist * Math.max(1, 1.15 / this.aspecto);
    return [
      cam.mira[0] + d * cp * Math.sin(cam.yaw),
      cam.mira[1] + d * Math.sin(cam.pitch),
      cam.mira[2] + d * cp * Math.cos(cam.yaw),
    ];
  }

  private matriz(): M4 {
    const c = this.lienzoRef.nativeElement;
    return mult(perspectiva(0.6, c.width / c.height, 0.5, 80), mirarA(this.ojo(), this.cam.mira, [0, 1, 0]));
  }

  private separacion(): number {
    return 0.02 + 1.15 * this.apertura;
  }

  private desplazo(p: Pieza | { superior: boolean }, t = 0): Vec3 {
    const s = this.separacion() * (p.superior ? 1 : -1);
    const off: Vec3 = [0, s, 0];
    if ('movilidad' in p && p.movilidad && !this.sinMovimiento) {
      const w = Math.sin(t / 95) * 0.022;
      off[0] += p.afuera[0] * w;
      off[2] += p.afuera[2] * w;
    }
    return off;
  }

  private bucle = (): void => {
    this.cuadro = requestAnimationFrame(this.bucle);
    const ahora = performance.now();
    const dt = Math.min(0.05, (ahora - this.ultimo) / 1000);
    this.ultimo = ahora;
    if (!this.arrastre.activo) {
      this.destino.yaw += this.vel.yaw;
      this.destino.pitch = Math.max(-1.38, Math.min(1.38, this.destino.pitch + this.vel.pitch));
      const roce = Math.pow(0.0025, dt);
      this.vel.yaw *= roce;
      this.vel.pitch *= roce;
    }
    if (this.girando()) this.destino.yaw += dt * 0.35;
    const k = 1 - Math.exp(-dt * (this.sinMovimiento ? 40 : 9));
    this.cam.yaw += (this.destino.yaw - this.cam.yaw) * k;
    this.cam.pitch += (this.destino.pitch - this.cam.pitch) * k;
    this.cam.dist += (this.destino.dist - this.cam.dist) * k;
    for (let i = 0; i < 3; i++) this.cam.mira[i] += (this.destino.mira[i] - this.cam.mira[i]) * k;
    this.apertura += (this.aperturaObjetivo - this.apertura) * (1 - Math.exp(-dt * 10));
    if (this.pendienteHover) {
      this.pendienteHover = false;
      this.calcularHover();
    }
    this.dibujar(ahora);
    this.ubicarEtiquetas();
  };

  private ver(superior: boolean): boolean {
    const a = this.arcada();
    return a === 'ambas' || (a === 'superior') === superior;
  }

  private dibujar(t: number): void {
    const gl = this.gl;
    const p = this.prog;
    if (!gl || !p) return;
    const c = this.lienzoRef.nativeElement;
    gl.viewport(0, 0, c.width, c.height);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.CULL_FACE);
    gl.disable(gl.CULL_FACE);
    gl.useProgram(p);
    gl.uniformMatrix4fv(this.loc['uMvp'], false, this.matriz());
    gl.uniform3fv(this.loc['uOjo'], this.ojo());
    const elegida = this.elegida();
    const hov = this.hoverFdi();
    const raices = this.raices();

    const malla = (b: Buffers, off: Vec3) => {
      gl.uniform3fv(this.loc['uOff'], off);
      for (const [nombre, buf] of [['aPos', b.pos], ['aNor', b.nor], ['aCol', b.col], ['aMat', b.mat]] as const) {
        const loc = this.atr[nombre];
        gl.bindBuffer(gl.ARRAY_BUFFER, buf);
        gl.enableVertexAttribArray(loc);
        gl.vertexAttribPointer(loc, 3, gl.FLOAT, false, 0, 0);
      }
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, b.idx);
      gl.drawElements(gl.TRIANGLES, b.n, gl.UNSIGNED_SHORT, 0);
    };
    const sinRealce = () => {
      gl.uniform1f(this.loc['uRimFuerza'], 0);
      gl.uniform1f(this.loc['uCara'], -1);
    };

    gl.disable(gl.BLEND);
    gl.depthMask(true);
    gl.uniform1f(this.loc['uAlfa'], 1);
    sinRealce();

    if (!raices) for (const e of this.encias) if (this.ver(e.superior)) malla(e.buf, this.desplazo(e));

    const pulso = 0.75 + 0.25 * Math.sin(t / 240);
    for (const { pieza, buf, raiz } of this.piezas) {
      if (pieza.ausente || !this.ver(pieza.superior)) continue;
      const off = this.desplazo(pieza, t);
      if (pieza.fdi === elegida) {
        gl.uniform3fv(this.loc['uRim'], [0.45, 0.95, 0.85]);
        gl.uniform1f(this.loc['uRimFuerza'], 1.4 * pulso);
      } else if (pieza.fdi === hov) {
        gl.uniform3fv(this.loc['uRim'], [1, 1, 1]);
        gl.uniform1f(this.loc['uRimFuerza'], 0.55);
      } else {
        gl.uniform1f(this.loc['uRimFuerza'], 0);
      }
      const caraHover = this.editable && pieza.fdi === hov && this.hoverCara ? CARAS.indexOf(this.hoverCara) : this.caraEsquema() && pieza.fdi === elegida ? CARAS.indexOf(this.caraEsquema()!) : -1;
      gl.uniform1f(this.loc['uCara'], caraHover);
      gl.uniform3fv(this.loc['uCaraColor'], this.pincel ? this.colorRgb(this.pincel.color) : [0.45, 0.95, 0.85]);
      malla(buf, off);
      gl.uniform1f(this.loc['uCara'], -1);
      if (raices && raiz) {
        gl.uniform1f(this.loc['uRimFuerza'], 0);
        malla(raiz, off);
      }
    }

    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.depthMask(false);
    sinRealce();
    if (raices) {
      gl.uniform1f(this.loc['uAlfa'], 0.3);
      for (const e of this.encias) if (this.ver(e.superior)) malla(e.buf, this.desplazo(e));
    }
    for (const { pieza, buf } of this.piezas) {
      if (!pieza.ausente || !this.ver(pieza.superior)) continue;
      const sel = pieza.fdi === elegida || pieza.fdi === hov;
      gl.uniform1f(this.loc['uAlfa'], sel ? 0.32 : 0.13);
      gl.uniform3fv(this.loc['uRim'], [0.6, 0.85, 0.95]);
      gl.uniform1f(this.loc['uRimFuerza'], sel ? 1.2 : 0.6);
      malla(buf, this.desplazo(pieza));
    }
    gl.depthMask(true);
  }

  private colorRgb(c: string): Vec3 {
    const n = parseInt(c.replace('#', ''), 16);
    return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
  }

  private proyectar(m: M4, p: Vec3): { x: number; y: number; ok: boolean } {
    const x = m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12];
    const y = m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13];
    const w = m[3] * p[0] + m[7] * p[1] + m[11] * p[2] + m[15];
    if (w <= 0.01) return { x: 0, y: 0, ok: false };
    const c = this.lienzoRef.nativeElement;
    return { x: ((x / w) * 0.5 + 0.5) * c.clientWidth, y: (1 - ((y / w) * 0.5 + 0.5)) * c.clientHeight, ok: true };
  }

  private ubicarEtiquetas(): void {
    const escena = this.escenaRef?.nativeElement;
    if (!escena || !this.boca) return;
    if (this.etiquetasDom.size === 0) {
      escena.querySelectorAll<HTMLElement>('.num[data-fdi]').forEach((el) => this.etiquetasDom.set(el.dataset['fdi']!, el));
    }
    const m = this.matriz();
    const ojo = this.ojo();
    const todos = this.numeros();
    const elegida = this.elegida();
    const hov = this.hoverFdi();
    for (const { pieza } of this.piezas) {
      const el = this.etiquetasDom.get(pieza.fdi);
      if (!el) continue;
      const off = this.desplazo(pieza);
      const a: Vec3 = [pieza.ancla[0] + off[0], pieza.ancla[1] + off[1], pieza.ancla[2] + off[2]];
      const q = this.proyectar(m, a);
      const frente = punto(pieza.afuera, norm(resta(ojo, a)));
      let op = Math.min(1, Math.max(0, (frente - 0.3) / 0.3));
      if (!this.ver(pieza.superior) || !q.ok) op = 0;
      const mostrar = todos || pieza.fdi === elegida || pieza.fdi === hov;
      el.style.opacity = String(mostrar ? op : 0);
      el.style.transform = `translate(${q.x - el.offsetWidth / 2}px, ${q.y - el.offsetHeight / 2}px)`;
    }
    const tip = this.tipRef?.nativeElement;
    if (tip && this.sobre) {
      const r = escena.getBoundingClientRect();
      const x = Math.min(this.sobre.x + 16, r.width - tip.offsetWidth - 8);
      const y = Math.min(this.sobre.y + 18, r.height - tip.offsetHeight - 8);
      tip.style.transform = `translate(${x}px, ${y}px)`;
    }
  }

  private rayo(cx: number, cy: number): { o: Vec3; d: Vec3 } {
    const c = this.lienzoRef.nativeElement;
    const nx = (cx / c.clientWidth) * 2 - 1;
    const ny = -((cy / c.clientHeight) * 2 - 1);
    const ojo = this.ojo();
    const z = norm(resta(ojo, this.cam.mira));
    const x = norm(cruz([0, 1, 0], z));
    const y = cruz(z, x);
    const t = Math.tan(0.6 / 2);
    const asp = c.width / c.height;
    const d = norm([
      -z[0] + x[0] * nx * t * asp + y[0] * ny * t,
      -z[1] + x[1] * nx * t * asp + y[1] * ny * t,
      -z[2] + x[2] * nx * t * asp + y[2] * ny * t,
    ]);
    return { o: ojo, d };
  }

  private buscar(cx: number, cy: number): { fdi: string; cara: Cara | null } | null {
    const { o, d } = this.rayo(cx, cy);
    let mejor: { fdi: string; t: number; cara: Cara | null } | null = null;
    for (const { pieza } of this.piezas) {
      if (!this.ver(pieza.superior)) continue;
      const off = this.desplazo(pieza);
      const oo: Vec3 = [o[0] - off[0], o[1] - off[1], o[2] - off[2]];
      const oc = resta(oo, pieza.centro);
      const b = punto(oc, d);
      if (b * b - (punto(oc, oc) - pieza.radio * pieza.radio * 1.7) < 0) continue;
      const golpe = this.rayoMalla(oo, d, pieza);
      if (golpe && (!mejor || golpe.t < mejor.t)) mejor = { fdi: pieza.fdi, t: golpe.t, cara: golpe.cara };
    }
    return mejor;
  }

  private rayoMalla(o: Vec3, d: Vec3, p: Pieza): { t: number; cara: Cara | null } | null {
    const P = p.posiciones;
    const I = p.indices;
    let mejor: { t: number; cara: Cara | null } | null = null;
    for (let k = 0; k < I.length; k += 3) {
      const a = I[k] * 3;
      const bb = I[k + 1] * 3;
      const c = I[k + 2] * 3;
      const e1: Vec3 = [P[bb] - P[a], P[bb + 1] - P[a + 1], P[bb + 2] - P[a + 2]];
      const e2: Vec3 = [P[c] - P[a], P[c + 1] - P[a + 1], P[c + 2] - P[a + 2]];
      const h = cruz(d, e2);
      const det = punto(e1, h);
      if (Math.abs(det) < 1e-9) continue;
      const f = 1 / det;
      const s: Vec3 = [o[0] - P[a], o[1] - P[a + 1], o[2] - P[a + 2]];
      const u = f * punto(s, h);
      if (u < 0 || u > 1) continue;
      const q = cruz(s, e1);
      const v = f * punto(d, q);
      if (v < 0 || u + v > 1) continue;
      const t = f * punto(e2, q);
      if (t > 1e-4 && (!mejor || t < mejor.t)) {
        const w = 1 - u - v;
        const vert = w >= u && w >= v ? I[k] : u >= v ? I[k + 1] : I[k + 2];
        const idx = p.caras[vert];
        mejor = { t, cara: idx >= 0 ? CARAS[idx] : null };
      }
    }
    return mejor;
  }

  private calcularHover(): void {
    if (!this.sobre || this.arrastre.activo) return;
    const r = this.buscar(this.sobre.x, this.sobre.y);
    const fdi = r?.fdi ?? this.mapaHover;
    const cara = r?.cara ?? null;
    if (fdi === this.hoverFdi() && cara === this.hoverCara) return;
    this.hoverCara = cara;
    this.zone.run(() => {
      this.hoverFdi.set(fdi);
      if (r) {
        const d = describirPieza(this.conditions ?? [], r.fdi);
        this.hover.set({
          fdi: r.fdi,
          nombre: nombrePieza(r.fdi),
          cara,
          resumen: d.length ? d.map((x) => x.etiqueta).slice(0, 3).join(' · ') : 'Sin hallazgos',
        });
      } else {
        this.hover.set(null);
      }
    });
    this.lienzoRef.nativeElement.style.cursor = r ? 'pointer' : '';
  }

  bajar(e: PointerEvent): void {
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    this.punteros.set(e.pointerId, { x: e.clientX, y: e.clientY });
    this.arrastre = { x: e.clientX, y: e.clientY, movido: 0, activo: true };
    this.vel = { yaw: 0, pitch: 0 };
    if (this.punteros.size === 2) this.pellizco = this.distanciaPunteros();
  }

  mover(e: PointerEvent): void {
    const r = this.lienzoRef.nativeElement.getBoundingClientRect();
    this.sobre = { x: e.clientX - r.left, y: e.clientY - r.top };
    const antes = this.punteros.get(e.pointerId);
    if (!antes) {
      if (e.pointerType === 'mouse') this.pendienteHover = true;
      return;
    }
    this.punteros.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (this.punteros.size === 2) {
      const d = this.distanciaPunteros();
      if (this.pellizco > 0) this.zoom(this.pellizco / d);
      this.pellizco = d;
      this.arrastre.movido += 10;
      return;
    }
    const dx = e.clientX - antes.x;
    const dy = e.clientY - antes.y;
    this.arrastre.movido += Math.abs(dx) + Math.abs(dy);
    if (this.arrastre.movido < 4) return;
    const k = 0.0072;
    this.destino.yaw -= dx * k;
    this.destino.pitch = Math.max(-1.38, Math.min(1.38, this.destino.pitch + dy * k));
    this.vel = { yaw: -dx * k * 0.55, pitch: dy * k * 0.55 };
    if (this.hover()) this.zone.run(() => this.hover.set(null));
    if (this.girando()) this.zone.run(() => this.girando.set(false));
    if (this.vistaActual()) this.zone.run(() => this.vistaActual.set(null));
  }

  subir(e: PointerEvent): void {
    this.punteros.delete(e.pointerId);
    if (this.punteros.size < 2) this.pellizco = 0;
    if (this.punteros.size === 0) this.arrastre.activo = false;
    if (this.arrastre.movido < 6 && e.type === 'pointerup') {
      this.vel = { yaw: 0, pitch: 0 };
      this.zone.run(() => this.tocar(e));
    }
  }

  salir(): void {
    if (this.arrastre.activo) return;
    this.sobre = null;
    this.hoverCara = null;
    if (this.hoverFdi() && !this.mapaHover) this.hoverFdi.set(null);
    this.hover.set(null);
  }

  rueda(e: WheelEvent): void {
    e.preventDefault();
    this.zoom(Math.exp(e.deltaY * 0.0012));
  }

  private zoom(f: number): void {
    this.destino.dist = Math.max(4.5, Math.min(24, this.destino.dist * f));
  }

  private distanciaPunteros(): number {
    const [a, b] = [...this.punteros.values()];
    return Math.hypot(a.x - b.x, a.y - b.y) || 1;
  }

  private tocar(e: PointerEvent): void {
    const r = this.lienzoRef.nativeElement.getBoundingClientRect();
    const g = this.buscar(e.clientX - r.left, e.clientY - r.top);
    if (!g) {
      this.elegir(null);
      return;
    }
    this.elegir(g.fdi);
    if (this.editable && g.cara) this.surfaceClicked.emit({ fdi: g.fdi, surface: g.cara });
  }

  dobleClic(e: MouseEvent): void {
    const r = this.lienzoRef.nativeElement.getBoundingClientRect();
    const g = this.buscar(e.clientX - r.left, e.clientY - r.top);
    if (g) this.enfocar(g.fdi);
    else this.restablecer();
  }

  tecla(e: KeyboardEvent): void {
    const paso = 0.18;
    const acciones: Record<string, () => void> = {
      ArrowLeft: () => (this.destino.yaw += paso),
      ArrowRight: () => (this.destino.yaw -= paso),
      ArrowUp: () => (this.destino.pitch = Math.max(-1.38, this.destino.pitch - paso)),
      ArrowDown: () => (this.destino.pitch = Math.min(1.38, this.destino.pitch + paso)),
      '+': () => this.zoom(0.85),
      '=': () => this.zoom(0.85),
      '-': () => this.zoom(1.18),
      Escape: () => this.elegir(null),
      r: () => this.restablecer(),
    };
    const f = acciones[e.key];
    if (f) {
      e.preventDefault();
      f();
      this.vistaActual.set(null);
    }
  }

  hoverMapa(fdi: string | null): void {
    this.mapaHover = fdi;
    this.hoverFdi.set(fdi);
  }

  elegir(fdi: string | null, avisar = true): void {
    this.elegida.set(fdi);
    this.caraEsquema.set(null);
    this.detalle.set(fdi ? describirPieza(this.conditions ?? [], fdi) : []);
    if (avisar) this.toothSelected.emit(fdi);
  }

  enfocar(fdi: string): void {
    const p = this.piezas.find((x) => x.pieza.fdi === fdi)?.pieza;
    if (!p) return;
    if (!this.ver(p.superior)) this.arcada.set('ambas');
    const off = this.desplazo(p);
    const base = Math.round(this.destino.yaw / (2 * Math.PI)) * 2 * Math.PI;
    let yaw = Math.atan2(p.afuera[0], p.afuera[2]);
    while (yaw - (this.destino.yaw - base) > Math.PI) yaw -= 2 * Math.PI;
    while (yaw - (this.destino.yaw - base) < -Math.PI) yaw += 2 * Math.PI;
    this.destino = {
      yaw: base + yaw,
      pitch: p.superior ? -0.12 : 0.32,
      dist: 6.2,
      mira: [p.centro[0] + off[0], p.centro[1] + off[1], p.centro[2] + off[2]],
    };
    this.vel = { yaw: 0, pitch: 0 };
    this.girando.set(false);
    this.vistaActual.set(null);
  }

  restablecer(): void {
    this.destino = { ...INICIO, yaw: Math.round(this.destino.yaw / (2 * Math.PI)) * 2 * Math.PI, mira: [...INICIO.mira] as Vec3 };
    this.vel = { yaw: 0, pitch: 0 };
    this.arcada.set('ambas');
    this.vistaActual.set('frente');
  }

  vista(v: Vista): void {
    this.girando.set(false);
    this.vel = { yaw: 0, pitch: 0 };
    const base = Math.round(this.destino.yaw / (2 * Math.PI)) * 2 * Math.PI;
    const tabla: Record<Vista, { yaw: number; pitch: number; dist: number }> = {
      frente: { yaw: 0, pitch: 0.16, dist: 12.4 },
      arriba: { yaw: 0, pitch: -1.36, dist: 11.5 },
      abajo: { yaw: 0, pitch: 1.36, dist: 11.5 },
      derecha: { yaw: -1.3, pitch: 0.12, dist: 11.5 },
      izquierda: { yaw: 1.3, pitch: 0.12, dist: 11.5 },
    };
    this.destino = { ...tabla[v], yaw: base + tabla[v].yaw, mira: [...INICIO.mira] as Vec3 };
    this.arcada.set(v === 'arriba' ? 'superior' : v === 'abajo' ? 'inferior' : 'ambas');
    this.vistaActual.set(v);
  }

  abrir(valor: number): void {
    this.aperturaObjetivo = valor;
  }

  tocarCara(fdi: string, cara: Cara | 'whole'): void {
    if (!this.editable) return;
    this.surfaceClicked.emit({ fdi, surface: cara });
  }

  nombre(fdi: string): string {
    return nombrePieza(fdi);
  }

  caraTexto(c: Cara): string {
    return (SURFACE_LABELS[c] ?? c).toLowerCase();
  }

  figuras(fdi: string): { cara: Cara; puntos: string; color: string | null; letra: string; tx: number; ty: number }[] {
    const q = Number(fdi[0]);
    const derechaPaciente = q === 1 || q === 4 || q === 5 || q === 8;
    const superior = q === 1 || q === 2 || q === 5 || q === 6;
    const hs = (this.conditions ?? []).filter((h) => h.fdi_number === fdi && h.condition !== 'sano');
    const color = (cara: Cara) => {
      const h = hs.find((x) => x.surface === cara) ?? hs.find((x) => x.surface === 'whole');
      return h ? TOOTH_CONDITION_BY_CODE[h.condition]?.color ?? null : null;
    };
    const arriba: Cara = superior ? 'vestibular' : 'lingual';
    const abajo: Cara = superior ? 'lingual' : 'vestibular';
    const izq: Cara = derechaPaciente ? 'distal' : 'mesial';
    const der: Cara = derechaPaciente ? 'mesial' : 'distal';
    const letra: Record<Cara, string> = { vestibular: 'V', lingual: superior ? 'P' : 'L', mesial: 'M', distal: 'D', oclusal: 'O' };
    return [
      { cara: arriba, puntos: '4,4 96,4 70,30 30,30', tx: 50, ty: 16 },
      { cara: abajo, puntos: '30,70 70,70 96,96 4,96', tx: 50, ty: 84 },
      { cara: izq, puntos: '4,4 30,30 30,70 4,96', tx: 16, ty: 50 },
      { cara: der, puntos: '70,30 96,4 96,96 70,70', tx: 84, ty: 50 },
      { cara: 'oclusal' as Cara, puntos: '30,30 70,30 70,70 30,70', tx: 50, ty: 50 },
    ].map((f) => ({ ...f, color: color(f.cara), letra: letra[f.cara] }));
  }

  async pantallaCompleta(): Promise<void> {
    const el = this.escenaRef.nativeElement.parentElement!;
    if (document.fullscreenElement) await document.exitFullscreen();
    else await el.requestFullscreen?.();
  }

  private alCambiarPantalla = (): void => {
    this.zone.run(() => this.completa.set(!!document.fullscreenElement));
    setTimeout(() => this.ajustar(), 50);
  };
}
