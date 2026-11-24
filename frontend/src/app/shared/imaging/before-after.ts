import { DatePipe } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import {
  Component,
  ElementRef,
  Injectable,
  Input,
  OnChanges,
  ViewChild,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Observable, firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';
import { BrandingService } from '../../core/branding/branding.service';
import { ClinicalImage } from '../../core/models/clinical-image.models';
import { confirmAction } from '../confirm-dialog/confirm-dialog.component';

export interface ImageMini {
  id: string;
  title: string;
  image_type: string;
  taken_on: string | null;
  created_at: string;
}

export interface Comparison {
  id: string;
  patient_id: string;
  title: string;
  treatment: string | null;
  notes: string | null;
  share_consent: boolean;
  share_consent_at: string | null;
  created_at: string;
  before: ImageMini;
  after: ImageMini;
}

export interface ComparisonFields {
  before_image_id?: string;
  after_image_id?: string;
  title?: string;
  treatment?: string | null;
  notes?: string | null;
  share_consent?: boolean;
}

@Injectable({ providedIn: 'root' })
export class ComparisonsService {
  private readonly http = inject(HttpClient);

  list(patientId: string): Observable<Comparison[]> {
    return this.http.get<Comparison[]>(`${environment.apiUrl}/patients/${patientId}/comparisons`);
  }

  create(patientId: string, body: ComparisonFields): Observable<Comparison> {
    return this.http.post<Comparison>(`${environment.apiUrl}/patients/${patientId}/comparisons`, body);
  }

  update(id: string, body: ComparisonFields): Observable<Comparison> {
    return this.http.put<Comparison>(`${environment.apiUrl}/comparisons/${id}`, body);
  }

  remove(id: string): Observable<void> {
    return this.http.delete<void>(`${environment.apiUrl}/comparisons/${id}`);
  }
}

function errorDe(e: unknown): string {
  if (e instanceof HttpErrorResponse) {
    const d = e.error?.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d) && d[0]?.msg) return String(d[0].msg).replace(/^Value error, /, '');
  }
  return 'No se pudo guardar. Intente de nuevo.';
}

const esImagen = (i: ClinicalImage) => (i.mime_type ?? '').startsWith('image/') && !i.archived_at;

@Component({
  selector: 'app-before-after-slider',
  standalone: true,
  template: `
    <div
      class="marco"
      #marco
      [class.lado]="modo === 'lado'"
      (pointerdown)="bajar($event)"
      (pointermove)="mover($event)"
      (pointerup)="soltar()"
      (pointercancel)="soltar()"
      tabindex="0"
      role="slider"
      aria-label="Comparar antes y después"
      [attr.aria-valuenow]="pos()"
      aria-valuemin="0"
      aria-valuemax="100"
      (keydown.arrowleft)="pos.set(max(0, pos() - 5))"
      (keydown.arrowright)="pos.set(min(100, pos() + 5))"
    >
      @if (modo === 'lado') {
        <figure><img [src]="antes" alt="Antes" draggable="false" /><figcaption>Antes</figcaption></figure>
        <figure><img [src]="despues" alt="Después" draggable="false" /><figcaption>Después</figcaption></figure>
      } @else {
        <img class="base" [src]="despues" alt="Después" draggable="false" />
        <img class="arriba" [src]="antes" alt="Antes" draggable="false" [style.clip-path]="'inset(0 ' + (100 - pos()) + '% 0 0)'" />
        <span class="etiqueta izq">Antes</span>
        <span class="etiqueta der">Después</span>
        <div class="linea" [style.left.%]="pos()"><span class="tirador">‹ ›</span></div>
      }
    </div>
  `,
  styles: [
    `
      .marco { position: relative; overflow: hidden; border-radius: 18px; background: #0f1a1c; user-select: none; touch-action: none; cursor: ew-resize; outline: none; }
      .marco:focus-visible { box-shadow: 0 0 0 3px var(--color-primary-soft); }
      img { display: block; width: 100%; max-height: 70vh; object-fit: contain; pointer-events: none; }
      .arriba { position: absolute; inset: 0; height: 100%; }
      .linea { position: absolute; top: 0; bottom: 0; width: 3px; margin-left: -1.5px; background: #fff; box-shadow: 0 0 12px rgba(0,0,0,.45); }
      .tirador { position: absolute; top: 50%; left: 50%; display: grid; place-items: center; width: 42px; height: 42px; margin: -21px 0 0 -21px;
        border-radius: 50%; background: #fff; color: #14242b; font-weight: 800; letter-spacing: 2px; box-shadow: 0 6px 18px rgba(0,0,0,.35); }
      .etiqueta { position: absolute; top: 12px; padding: 4px 10px; border-radius: 999px; background: rgba(15,26,28,.72); color: #fff;
        font-size: .72rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
      .izq { left: 12px; } .der { right: 12px; }
      .lado { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; cursor: default; background: transparent; }
      figure { position: relative; margin: 0; border-radius: 14px; overflow: hidden; background: #0f1a1c;
        figcaption { position: absolute; left: 10px; top: 10px; padding: 3px 9px; border-radius: 999px; background: rgba(15,26,28,.72); color: #fff;
          font-size: .7rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; } }
    `,
  ],
})
export class BeforeAfterSliderComponent {
  @Input({ required: true }) antes!: string;
  @Input({ required: true }) despues!: string;
  @Input() modo: 'deslizar' | 'lado' = 'deslizar';
  @ViewChild('marco') private marco!: ElementRef<HTMLDivElement>;
  readonly pos = signal(50);
  readonly max = Math.max;
  readonly min = Math.min;
  private arrastrando = false;

  bajar(e: PointerEvent): void {
    if (this.modo === 'lado') return;
    this.arrastrando = true;
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
    this.mover(e);
  }

  mover(e: PointerEvent): void {
    if (!this.arrastrando) return;
    const r = this.marco.nativeElement.getBoundingClientRect();
    this.pos.set(Math.max(0, Math.min(100, ((e.clientX - r.left) / r.width) * 100)));
  }

  soltar(): void {
    this.arrastrando = false;
  }
}

function cargarImagen(src: string): Promise<HTMLImageElement> {
  return new Promise((ok, mal) => {
    const i = new Image();
    i.onload = () => ok(i);
    i.onerror = mal;
    i.src = src;
  });
}

function cubrir(ctx: CanvasRenderingContext2D, img: HTMLImageElement, x: number, y: number, w: number, h: number, r: number): void {
  const k = Math.max(w / img.width, h / img.height);
  const sw = w / k;
  const sh = h / k;
  ctx.save();
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
  ctx.clip();
  ctx.drawImage(img, (img.width - sw) / 2, (img.height - sh) / 2, sw, sh, x, y, w, h);
  ctx.restore();
}

function pastilla(ctx: CanvasRenderingContext2D, texto: string, x: number, y: number, fondo: string): void {
  ctx.font = '700 30px Inter, Arial, sans-serif';
  const w = ctx.measureText(texto).width + 44;
  ctx.fillStyle = fondo;
  ctx.beginPath();
  ctx.roundRect(x, y, w, 54, 27);
  ctx.fill();
  ctx.fillStyle = '#fff';
  ctx.textBaseline = 'middle';
  ctx.fillText(texto, x + 22, y + 28);
}

export async function imagenParaRedes(
  antesUrl: string,
  despuesUrl: string,
  formato: 'vertical' | 'horizontal',
  marca: { nombre: string; color: string; logo: string | null; eslogan: string | null },
  titulo: string,
): Promise<Blob> {
  const [antes, despues] = await Promise.all([cargarImagen(antesUrl), cargarImagen(despuesUrl)]);
  const W = formato === 'vertical' ? 1080 : 1600;
  const H = formato === 'vertical' ? 1350 : 900;
  const c = document.createElement('canvas');
  c.width = W;
  c.height = H;
  const ctx = c.getContext('2d')!;
  ctx.fillStyle = '#f6f4ef';
  ctx.fillRect(0, 0, W, H);
  // Franja de marca arriba.
  ctx.fillStyle = marca.color;
  ctx.fillRect(0, 0, W, 8);

  const m = 48;
  let y = 46;
  let xTexto = m;
  if (marca.logo) {
    try {
      const logo = await cargarImagen(marca.logo);
      const lh = 86;
      const lw = (logo.width / logo.height) * lh;
      ctx.drawImage(logo, m, y, lw, lh);
      xTexto = m + lw + 22;
    } catch {
      // Sin logo legible, solo el nombre.
    }
  }
  ctx.fillStyle = '#14242b';
  ctx.textBaseline = 'alphabetic';
  ctx.font = '800 40px "Plus Jakarta Sans", Inter, Arial, sans-serif';
  ctx.fillText(marca.nombre, xTexto, y + 44);
  if (marca.eslogan) {
    ctx.fillStyle = '#5d6b6d';
    ctx.font = '500 26px Inter, Arial, sans-serif';
    ctx.fillText(marca.eslogan, xTexto, y + 80);
  }
  y += 120;

  const pie = 130;
  const alto = H - y - pie - m;
  if (formato === 'vertical') {
    const h = (alto - 16) / 2;
    cubrir(ctx, antes, m, y, W - 2 * m, h, 26);
    cubrir(ctx, despues, m, y + h + 16, W - 2 * m, h, 26);
    pastilla(ctx, 'ANTES', m + 20, y + 20, 'rgba(15,26,28,.78)');
    pastilla(ctx, 'DESPUÉS', m + 20, y + h + 36, marca.color);
  } else {
    const w = (W - 2 * m - 16) / 2;
    cubrir(ctx, antes, m, y, w, alto, 26);
    cubrir(ctx, despues, m + w + 16, y, w, alto, 26);
    pastilla(ctx, 'ANTES', m + 20, y + 20, 'rgba(15,26,28,.78)');
    pastilla(ctx, 'DESPUÉS', m + w + 36, y + 20, marca.color);
  }

  ctx.fillStyle = '#14242b';
  ctx.font = '800 46px "Plus Jakarta Sans", Inter, Arial, sans-serif';
  ctx.textBaseline = 'alphabetic';
  ctx.fillText(titulo, m, H - m - 52);
  ctx.fillStyle = '#5d6b6d';
  ctx.font = '500 26px Inter, Arial, sans-serif';
  ctx.fillText('Resultado real de un paciente, publicado con su autorización.', m, H - m - 10);

  return new Promise((ok) => c.toBlob((b) => ok(b!), 'image/png'));
}

interface FormData {
  patientId: string;
  images: ClinicalImage[];
  previews: Record<string, string>;
  comparison?: Comparison | null;
}

@Component({
  selector: 'app-comparison-form',
  standalone: true,
  imports: [DatePipe, FormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatIconModule, MatInputModule, MatSlideToggleModule],
  template: `
    <h2 mat-dialog-title>{{ data.comparison ? 'Editar comparación' : 'Nuevo antes y después' }}</h2>
    <mat-dialog-content>
      @if (fotos.length < 2) {
        <p class="vacio">Suba al menos dos fotos del paciente (por ejemplo una antes del tratamiento y otra al terminar) para compararlas.</p>
      } @else {
        <p class="paso"><b>1.</b> Toque la foto del <b class="antes">ANTES</b> y luego la del <b class="despues">DESPUÉS</b>.</p>
        <div class="fotos">
          @for (f of fotos; track f.id) {
            <button type="button" class="foto" [class.antes]="antes() === f.id" [class.despues]="despues() === f.id" (click)="tocar(f.id)">
              @if (data.previews[f.id]) { <img [src]="data.previews[f.id]" alt="" /> } @else { <span class="sin">Cargando…</span> }
              <span class="pie">{{ f.title }}<small>{{ (f.taken_on || f.created_at) | date: 'dd/MM/yyyy' }}</small></span>
              @if (antes() === f.id) { <span class="marca">ANTES</span> }
              @if (despues() === f.id) { <span class="marca d">DESPUÉS</span> }
            </button>
          }
        </div>
        <p class="paso"><b>2.</b> Datos de la comparación</p>
        <div class="dialog-grid">
          <mat-form-field appearance="outline">
            <mat-label>Título</mat-label>
            <input matInput [(ngModel)]="titulo" maxlength="120" placeholder="Ej.: Blanqueamiento dental" />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Tratamiento (opcional)</mat-label>
            <input matInput [(ngModel)]="tratamiento" maxlength="120" placeholder="Ej.: Carillas de resina" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Notas (opcional)</mat-label>
            <textarea matInput rows="2" [(ngModel)]="notas"></textarea>
          </mat-form-field>
        </div>
        <label class="permiso">
          <mat-slide-toggle [(ngModel)]="permiso" />
          <span>
            <b>El paciente autorizó usar estas fotos en redes y publicidad</b>
            <small>Sin esta autorización la comparación solo se ve dentro del sistema. Queda registrado con la fecha y quién la marcó.</small>
          </span>
        </label>
      }
      @if (error()) { <p class="err">{{ error() }}</p> }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>Cancelar</button>
      @if (fotos.length >= 2) {
        <button mat-flat-button (click)="guardar()" [disabled]="guardando() || !antes() || !despues() || !titulo.trim()">Guardar</button>
      }
    </mat-dialog-actions>
  `,
  styles: [
    `
      .paso { margin: 4px 0 10px; font-size: .88rem; .antes { color: #5d6b6d; } .despues { color: var(--color-primary); } }
      .fotos { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; max-height: 340px; overflow: auto; padding: 2px; margin-bottom: 14px; }
      .foto { position: relative; display: grid; padding: 0; border: 2px solid transparent; border-radius: 14px; overflow: hidden; cursor: pointer; background: var(--color-surface-muted); text-align: left;
        img { width: 100%; height: 110px; object-fit: cover; display: block; }
        .sin { display: grid; place-items: center; height: 110px; font-size: .75rem; color: var(--color-ink-faint); }
        .pie { display: grid; padding: 6px 8px; font-size: .76rem; font-weight: 600; small { font-weight: 400; color: var(--color-ink-faint); } }
        &.antes { border-color: #5d6b6d; } &.despues { border-color: var(--color-primary); } }
      .marca { position: absolute; top: 6px; left: 6px; padding: 2px 8px; border-radius: 999px; background: #5d6b6d; color: #fff; font-size: .64rem; font-weight: 800; letter-spacing: .06em; }
      .marca.d { background: var(--color-primary); }
      .permiso { display: flex; gap: 12px; align-items: flex-start; padding: 12px; border-radius: var(--radius-md); background: var(--color-surface-muted);
        span { display: grid; gap: 2px; font-size: .86rem; } small { color: var(--color-ink-faint); font-size: .76rem; } }
      .vacio { color: var(--color-ink-faint); font-size: .88rem; }
      .err { color: var(--color-danger); font-size: .84rem; margin: 8px 0 0; }
    `,
  ],
})
export class ComparisonFormComponent {
  readonly data = inject<FormData>(MAT_DIALOG_DATA);
  private readonly ref = inject(MatDialogRef<ComparisonFormComponent, Comparison>);
  private readonly api = inject(ComparisonsService);
  readonly fotos = this.data.images.filter(esImagen);
  readonly antes = signal<string | null>(this.data.comparison?.before.id ?? null);
  readonly despues = signal<string | null>(this.data.comparison?.after.id ?? null);
  titulo = this.data.comparison?.title ?? '';
  tratamiento = this.data.comparison?.treatment ?? '';
  notas = this.data.comparison?.notes ?? '';
  permiso = this.data.comparison?.share_consent ?? false;
  readonly guardando = signal(false);
  readonly error = signal<string | null>(null);

  tocar(id: string): void {
    if (this.antes() === id) return this.antes.set(null);
    if (this.despues() === id) return this.despues.set(null);
    if (!this.antes()) this.antes.set(id);
    else if (!this.despues()) this.despues.set(id);
    else this.despues.set(id);
  }

  async guardar(): Promise<void> {
    const body: ComparisonFields = {
      before_image_id: this.antes()!,
      after_image_id: this.despues()!,
      title: this.titulo.trim(),
      treatment: this.tratamiento.trim() || null,
      notes: this.notas.trim() || null,
      share_consent: this.permiso,
    };
    this.guardando.set(true);
    this.error.set(null);
    try {
      const c = this.data.comparison;
      this.ref.close(await firstValueFrom(c ? this.api.update(c.id, body) : this.api.create(this.data.patientId, body)));
    } catch (e) {
      this.error.set(errorDe(e));
    } finally {
      this.guardando.set(false);
    }
  }
}

interface VisorData {
  comparison: Comparison;
  antes: string;
  despues: string;
  canWrite: boolean;
}

@Component({
  selector: 'app-comparison-viewer',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatButtonToggleModule, MatDialogModule, MatIconModule, MatTooltipModule, BeforeAfterSliderComponent],
  template: `
    <div class="cabeza">
      <div>
        <h2>{{ c.title }}</h2>
        <p>
          {{ c.treatment ? c.treatment + ' · ' : '' }}Antes {{ (c.before.taken_on || c.before.created_at) | date: 'dd/MM/yyyy' }} ·
          Después {{ (c.after.taken_on || c.after.created_at) | date: 'dd/MM/yyyy' }}
        </p>
      </div>
      <mat-button-toggle-group [value]="modo()" (change)="modo.set($event.value)">
        <mat-button-toggle value="deslizar">Deslizar</mat-button-toggle>
        <mat-button-toggle value="lado">Lado a lado</mat-button-toggle>
      </mat-button-toggle-group>
      <button mat-icon-button mat-dialog-close aria-label="Cerrar"><mat-icon>close</mat-icon></button>
    </div>
    <mat-dialog-content>
      <app-before-after-slider [antes]="data.antes" [despues]="data.despues" [modo]="modo()" />
      @if (c.notes) { <p class="notas">{{ c.notes }}</p> }
    </mat-dialog-content>
    <mat-dialog-actions>
      @if (c.share_consent) {
        <span class="ok"><mat-icon>verified_user</mat-icon>Autorizado para redes · {{ c.share_consent_at | date: 'dd/MM/yyyy' }}</span>
      } @else {
        <span class="no"><mat-icon>lock</mat-icon>Sin autorización para redes</span>
      }
      <span class="espacio"></span>
      @if (data.canWrite) {
        <button mat-button class="peligro" (click)="cerrarCon('eliminar')"><mat-icon>delete</mat-icon>Eliminar</button>
        <button mat-button (click)="cerrarCon('editar')"><mat-icon>edit</mat-icon>Editar</button>
      }
      <button
        mat-flat-button
        [disabled]="!c.share_consent || generando()"
        [matTooltip]="c.share_consent ? '' : 'Primero registre la autorización del paciente (Editar)'"
        (click)="paraRedes('vertical')"
      >
        <mat-icon>ios_share</mat-icon>Imagen para redes
      </button>
      <button mat-stroked-button [disabled]="!c.share_consent || generando()" (click)="paraRedes('horizontal')" matTooltip="Formato horizontal (web, Facebook)">
        <mat-icon>crop_landscape</mat-icon>
      </button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      .cabeza { display: flex; align-items: center; gap: 12px; padding: 18px 24px 8px; flex-wrap: wrap;
        > div { flex: 1; min-width: 200px; } h2 { margin: 0; font-size: 1.15rem; } p { margin: 2px 0 0; font-size: .8rem; color: var(--color-ink-faint); } }
      .notas { margin: 10px 0 0; font-size: .86rem; color: var(--color-ink-soft); }
      mat-dialog-actions { gap: 6px; flex-wrap: wrap; padding: 8px 24px 18px; }
      .ok, .no { display: inline-flex; align-items: center; gap: 6px; font-size: .8rem; mat-icon { font-size: 18px; width: 18px; height: 18px; } }
      .ok { color: var(--color-success); } .no { color: var(--color-ink-faint); }
      .espacio { flex: 1; }
      .peligro { color: var(--color-danger); }
    `,
  ],
})
export class ComparisonViewerComponent {
  readonly data = inject<VisorData>(MAT_DIALOG_DATA);
  private readonly ref = inject(MatDialogRef<ComparisonViewerComponent, 'editar' | 'eliminar'>);
  private readonly branding = inject(BrandingService);
  private readonly snack = inject(MatSnackBar);
  readonly c = this.data.comparison;
  readonly modo = signal<'deslizar' | 'lado'>('deslizar');
  readonly generando = signal(false);

  cerrarCon(accion: 'editar' | 'eliminar'): void {
    this.ref.close(accion);
  }

  async paraRedes(formato: 'vertical' | 'horizontal'): Promise<void> {
    this.generando.set(true);
    try {
      const b = this.branding.branding();
      const blob = await imagenParaRedes(
        this.data.antes,
        this.data.despues,
        formato,
        { nombre: this.branding.name(), color: b?.primary_color ?? '#0D7F76', logo: this.branding.logo(), eslogan: b?.slogan ?? null },
        this.c.treatment || this.c.title,
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `antes-despues-${this.c.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-${formato}.png`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 30_000);
      this.snack.open('Imagen descargada. Ya puede publicarla.', undefined, { duration: 2500 });
    } catch {
      this.snack.open('No se pudo generar la imagen.', 'Cerrar', { duration: 4000 });
    } finally {
      this.generando.set(false);
    }
  }
}

@Component({
  selector: 'app-before-after-section',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatIconModule],
  template: `
    <section class="seccion">
      <header>
        <div>
          <h3>Antes y después</h3>
          <p>Compare dos fotos del paciente con un deslizador. Con su autorización, genere la imagen para redes con su logo.</p>
        </div>
        @if (canWrite) {
          <button mat-stroked-button (click)="nueva()" [disabled]="fotos().length < 2"><mat-icon>compare</mat-icon>Nuevo antes y después</button>
        }
      </header>
      @if (lista().length === 0) {
        <p class="vacio">
          {{ fotos().length < 2 ? 'Suba al menos dos fotos para poder compararlas.' : 'Todavía no hay comparaciones.' }}
        </p>
      } @else {
        <div class="tarjetas">
          @for (c of lista(); track c.id) {
            <button type="button" class="tarjeta" (click)="abrir(c)">
              <div class="miniatura">
                @if (previews[c.before.id]) { <img [src]="previews[c.before.id]" alt="Antes" /> }
                @if (previews[c.after.id]) { <img class="d" [src]="previews[c.after.id]" alt="Después" /> }
                <span class="corte"></span>
              </div>
              <strong>{{ c.title }}</strong>
              <small>{{ c.treatment || 'Comparación' }} · {{ c.created_at | date: 'dd/MM/yyyy' }}</small>
              @if (c.share_consent) { <span class="tag"><mat-icon>verified_user</mat-icon>Autorizado para redes</span> }
            </button>
          }
        </div>
      }
    </section>
  `,
  styles: [
    `
      .seccion { margin-top: 18px; }
      header { display: flex; align-items: flex-end; gap: 12px; flex-wrap: wrap; margin-bottom: 10px;
        > div { flex: 1; min-width: 220px; } h3 { margin: 0; font-size: 1rem; } p { margin: 2px 0 0; font-size: .78rem; color: var(--color-ink-faint); } }
      .vacio { font-size: .84rem; color: var(--color-ink-faint); }
      .tarjetas { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
      .tarjeta { display: grid; gap: 4px; padding: 8px 8px 12px; border: 1px solid var(--color-border); border-radius: 16px; background: var(--color-surface);
        text-align: left; cursor: pointer; transition: transform .15s, box-shadow .15s;
        &:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
        strong { font-size: .9rem; } small { font-size: .74rem; color: var(--color-ink-faint); } }
      .miniatura { position: relative; height: 130px; border-radius: 12px; overflow: hidden; background: #0f1a1c;
        img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
        img.d { clip-path: inset(0 0 0 50%); }
        .corte { position: absolute; top: 0; bottom: 0; left: 50%; width: 2px; background: #fff; } }
      .tag { display: inline-flex; align-items: center; gap: 4px; font-size: .7rem; color: var(--color-success); font-weight: 600;
        mat-icon { font-size: 15px; width: 15px; height: 15px; } }
    `,
  ],
})
export class BeforeAfterSectionComponent implements OnChanges {
  @Input({ required: true }) patientId!: string;
  @Input() images: ClinicalImage[] = [];
  @Input() previews: Record<string, string> = {};
  @Input() canWrite = false;

  private readonly api = inject(ComparisonsService);
  private readonly dialog = inject(MatDialog);
  private readonly snack = inject(MatSnackBar);
  readonly lista = signal<Comparison[]>([]);
  private readonly imgs = signal<ClinicalImage[]>([]);
  readonly fotos = computed(() => this.imgs().filter(esImagen));
  private cargado: string | null = null;

  ngOnChanges(): void {
    this.imgs.set(this.images);
    if (this.cargado !== this.patientId) {
      this.cargado = this.patientId;
      void this.recargar();
    }
  }

  async recargar(): Promise<void> {
    try {
      this.lista.set(await firstValueFrom(this.api.list(this.patientId)));
    } catch {
      this.lista.set([]);
    }
  }

  async nueva(c?: Comparison): Promise<void> {
    const ref = this.dialog.open(ComparisonFormComponent, {
      data: { patientId: this.patientId, images: this.images, previews: this.previews, comparison: c ?? null },
      width: '820px',
      maxWidth: '96vw',
      panelClass: 'app-dialog',
    });
    const out = await firstValueFrom(ref.afterClosed());
    if (out) {
      await this.recargar();
      this.snack.open(c ? 'Comparación actualizada.' : 'Comparación creada.', undefined, { duration: 2000 });
      if (!c) this.abrir(out);
    }
  }

  async abrir(c: Comparison): Promise<void> {
    const antes = this.previews[c.before.id];
    const despues = this.previews[c.after.id];
    if (!antes || !despues) {
      this.snack.open('Las fotos todavía se están cargando. Intente en un momento.', undefined, { duration: 2500 });
      return;
    }
    const ref = this.dialog.open(ComparisonViewerComponent, {
      data: { comparison: c, antes, despues, canWrite: this.canWrite },
      width: '980px',
      maxWidth: '96vw',
      panelClass: 'app-dialog',
      autoFocus: false,
    });
    const accion = await firstValueFrom(ref.afterClosed());
    if (accion === 'editar') await this.nueva(c);
    if (accion === 'eliminar') {
      const ok = await confirmAction(this.dialog, {
        title: `¿Eliminar «${c.title}»?`,
        message: 'Solo se borra la comparación. Las fotos siguen en la historia clínica.',
        confirmLabel: 'Eliminar',
        danger: true,
      });
      if (ok) {
        await firstValueFrom(this.api.remove(c.id));
        await this.recargar();
      }
    }
  }
}
