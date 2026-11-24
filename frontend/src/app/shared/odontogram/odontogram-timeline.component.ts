import { DatePipe } from '@angular/common';
import { Component, EventEmitter, Input, OnChanges, OnDestroy, Output, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { firstValueFrom } from 'rxjs';

import { OdontogramTimelineEntry, TimelineFinding } from '../../core/models/odontogram.models';
import { OdontogramService } from '../../core/services/odontogram.service';
import { SURFACE_LABELS, TOOTH_CONDITION_BY_CODE } from './tooth-conditions';

const POR_TRATAR = new Set(['caries', 'restauracion_defectuosa', 'tratamiento_pendiente', 'extraccion_indicada', 'fractura']);

@Component({
  selector: 'app-odontogram-timeline',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatIconModule, MatTooltipModule],
  template: `
    <section class="linea glass-card">
      <header>
        <div>
          <h3><mat-icon>timeline</mat-icon>Línea de tiempo de la boca</h3>
          <p>{{ versiones().length }} {{ versiones().length === 1 ? 'versión guardada' : 'versiones guardadas' }} · elija una fecha para ver la boca de ese día</p>
        </div>
        <div class="mandos">
          <button mat-icon-button (click)="ir(0)" [disabled]="indice() <= 0" matTooltip="Primera"><mat-icon>first_page</mat-icon></button>
          <button mat-icon-button (click)="ir(indice() - 1)" [disabled]="indice() <= 0" matTooltip="Anterior"><mat-icon>chevron_left</mat-icon></button>
          <button mat-flat-button class="play" (click)="alternar()" [disabled]="versiones().length < 2">
            <mat-icon>{{ reproduciendo() ? 'pause' : 'play_arrow' }}</mat-icon>{{ reproduciendo() ? 'Pausa' : 'Reproducir' }}
          </button>
          <button mat-icon-button (click)="ir(indice() + 1)" [disabled]="indice() >= versiones().length - 1" matTooltip="Siguiente"><mat-icon>chevron_right</mat-icon></button>
          <button mat-icon-button (click)="ir(versiones().length - 1)" [disabled]="indice() >= versiones().length - 1" matTooltip="Actual"><mat-icon>last_page</mat-icon></button>
          <button mat-icon-button (click)="cerrar()" matTooltip="Cerrar y volver a la actual"><mat-icon>close</mat-icon></button>
        </div>
      </header>

      @if (cargando()) {
        <p class="vacio">Cargando versiones…</p>
      } @else if (versiones().length === 0) {
        <p class="vacio">Todavía no hay versiones guardadas. Cada vez que se guarda el odontograma se agrega un punto a la línea.</p>
      } @else {
        <div class="riel">
          <span class="base"></span>
          <span class="avance" [style.width.%]="posicion(indice())"></span>
          @for (v of versiones(); track v.id; let i = $index) {
            <button
              type="button"
              class="punto"
              [class.on]="i === indice()"
              [class.pasado]="i < indice()"
              [style.left.%]="posicion(i)"
              (click)="ir(i)"
              [matTooltip]="(v.created_at | date: 'd MMM y') + ' · ' + resumen(v)"
            ></button>
          }
        </div>
        <div class="fechas">
          <span>{{ versiones()[0].created_at | date: 'd MMM y' }}</span>
          @if (versiones().length > 1) { <span>{{ versiones()[versiones().length - 1].created_at | date: 'd MMM y' }}</span> }
        </div>

        @if (actual(); as v) {
          <div class="detalle">
            <div class="cuando">
              <strong>{{ v.created_at | date: "EEEE d 'de' MMMM 'de' y" }}</strong>
              <span>
                {{ indice() === 0 ? 'Inicial' : 'Seguimiento' }}{{ indice() === versiones().length - 1 ? ' · vigente' : '' }}
                @if (v.author_name) { · {{ v.author_name }} }
              </span>
              @if (v.notes) { <em>{{ v.notes }}</em> }
            </div>
            <div class="cifras">
              <span><b>{{ piezas(v.conditions) }}</b> piezas con hallazgos</span>
              <span class="alerta"><b>{{ porTratar(v.conditions) }}</b> por tratar</span>
            </div>
          </div>
          <div class="cambios">
            @if (indice() === 0) {
              <span class="titulo">Así empezó:</span>
            } @else {
              <span class="titulo">Cambios en esta visita:</span>
            }
            @for (c of v.added; track $index) {
              <button type="button" class="cambio mas" (click)="pieza.emit(c.fdi_number)">
                <i [style.background]="color(c)"></i>+ {{ etiqueta(c) }} · {{ c.fdi_number }} {{ cara(c) }}
              </button>
            }
            @for (c of v.removed; track $index) {
              <button type="button" class="cambio menos" (click)="pieza.emit(c.fdi_number)">
                <i [style.background]="color(c)"></i>− {{ etiqueta(c) }} · {{ c.fdi_number }} {{ cara(c) }}
              </button>
            }
            @if (!v.added.length && !v.removed.length) { <span class="sin">Sin cambios respecto a la anterior.</span> }
          </div>
        }
      }
    </section>
  `,
  styles: [
    `
      .linea { padding: 14px 18px 16px; margin-bottom: 14px; }
      header { display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
        > div:first-child { flex: 1; min-width: 220px; }
        h3 { display: flex; align-items: center; gap: 8px; margin: 0; font-size: 1rem; mat-icon { color: var(--color-primary); } }
        p { margin: 2px 0 0; font-size: .76rem; color: var(--color-ink-faint); } }
      .mandos { display: flex; align-items: center; gap: 2px; .play { margin: 0 4px; } }
      .vacio { margin: 12px 0 0; font-size: .84rem; color: var(--color-ink-faint); }
      .riel { position: relative; height: 34px; margin: 18px 12px 4px; }
      .base, .avance { position: absolute; top: 15px; left: 0; height: 4px; border-radius: 4px; }
      .base { right: 0; background: var(--color-border-strong); }
      .avance { background: var(--color-primary); transition: width .35s ease; }
      .punto { position: absolute; top: 8px; width: 18px; height: 18px; margin-left: -9px; padding: 0; border-radius: 50%; cursor: pointer;
        border: 3px solid var(--color-border-strong); background: var(--color-surface); transition: transform .2s, border-color .2s;
        &.pasado { border-color: var(--color-primary); }
        &.on { border-color: var(--color-primary); background: var(--color-primary); transform: scale(1.35); box-shadow: 0 0 0 6px var(--color-primary-soft); }
        &:hover { transform: scale(1.25); } }
      .fechas { display: flex; justify-content: space-between; margin: 0 4px; font-size: .72rem; color: var(--color-ink-faint); }
      .detalle { display: flex; flex-wrap: wrap; align-items: flex-start; gap: 10px 18px; margin-top: 14px;
        .cuando { display: grid; flex: 1; min-width: 220px; strong { font-size: .95rem; } strong::first-letter { text-transform: uppercase; } span { font-size: .78rem; color: var(--color-ink-soft); }
          em { font-size: .78rem; color: var(--color-ink-faint); } }
        .cifras { display: flex; gap: 8px; span { padding: 4px 10px; border-radius: 999px; background: var(--color-surface-muted); font-size: .78rem; }
          .alerta b { color: var(--color-danger); } } }
      .cambios { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 10px;
        .titulo { font-size: .76rem; font-weight: 600; color: var(--color-ink-soft); margin-right: 2px; }
        .sin { font-size: .8rem; color: var(--color-ink-faint); } }
      .cambio { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; border: 1px solid; background: transparent;
        font: inherit; font-size: .76rem; font-weight: 600; cursor: pointer;
        i { width: 9px; height: 9px; border-radius: 3px; }
        &.mas { border-color: color-mix(in srgb, var(--color-success) 45%, transparent); color: var(--color-success); background: var(--color-success-soft); }
        &.menos { border-color: color-mix(in srgb, var(--color-danger) 40%, transparent); color: var(--color-danger); background: var(--color-danger-soft); text-decoration: line-through; } }
    `,
  ],
})
export class OdontogramTimelineComponent implements OnChanges, OnDestroy {
  @Input({ required: true }) patientId!: string;
  /** Hallazgos de la versión elegida (null = volver a la vigente). */
  @Output() version = new EventEmitter<{ id: string; created_at: string; conditions: TimelineFinding[] } | null>();
  @Output() pieza = new EventEmitter<string>();
  @Output() cerrada = new EventEmitter<void>();

  private readonly api = inject(OdontogramService);
  readonly versiones = signal<OdontogramTimelineEntry[]>([]);
  readonly indice = signal(0);
  readonly cargando = signal(true);
  readonly reproduciendo = signal(false);
  readonly actual = computed(() => this.versiones()[this.indice()] ?? null);
  private reloj: ReturnType<typeof setInterval> | null = null;

  async ngOnChanges(): Promise<void> {
    this.cargando.set(true);
    try {
      const v = await firstValueFrom(this.api.getTimeline(this.patientId));
      this.versiones.set(v);
      // Se empieza por la primera: así la línea se recorre hacia adelante.
      if (v.length) this.ir(0);
    } finally {
      this.cargando.set(false);
    }
  }

  ngOnDestroy(): void {
    this.parar();
  }

  posicion(i: number): number {
    const v = this.versiones();
    if (v.length < 2) return 50;
    const t0 = new Date(v[0].created_at).getTime();
    const t1 = new Date(v[v.length - 1].created_at).getTime();
    if (t1 === t0) return (i / (v.length - 1)) * 100;
    return ((new Date(v[i].created_at).getTime() - t0) / (t1 - t0)) * 100;
  }

  ir(i: number): void {
    const v = this.versiones();
    if (!v.length) return;
    const k = Math.max(0, Math.min(v.length - 1, i));
    this.indice.set(k);
    // La última es la vigente: se vuelve al odontograma editable.
    this.version.emit(k === v.length - 1 ? null : { id: v[k].id, created_at: v[k].created_at, conditions: v[k].conditions });
  }

  alternar(): void {
    if (this.reproduciendo()) return this.parar();
    if (this.indice() >= this.versiones().length - 1) this.ir(0);
    this.reproduciendo.set(true);
    this.reloj = setInterval(() => {
      if (this.indice() >= this.versiones().length - 1) return this.parar();
      this.ir(this.indice() + 1);
    }, 1700);
  }

  private parar(): void {
    this.reproduciendo.set(false);
    if (this.reloj) clearInterval(this.reloj);
    this.reloj = null;
  }

  cerrar(): void {
    this.parar();
    this.version.emit(null);
    this.cerrada.emit();
  }

  piezas(c: TimelineFinding[]): number {
    return new Set(c.map((x) => x.fdi_number)).size;
  }

  porTratar(c: TimelineFinding[]): number {
    return new Set(c.filter((x) => POR_TRATAR.has(x.condition)).map((x) => x.fdi_number)).size;
  }

  resumen(v: OdontogramTimelineEntry): string {
    const partes = [];
    if (v.added.length) partes.push(`+${v.added.length}`);
    if (v.removed.length) partes.push(`−${v.removed.length}`);
    return partes.length ? `${partes.join(' ')} cambios` : 'sin cambios';
  }

  etiqueta(c: TimelineFinding): string {
    return TOOTH_CONDITION_BY_CODE[c.condition]?.label ?? c.condition;
  }

  color(c: TimelineFinding): string {
    return TOOTH_CONDITION_BY_CODE[c.condition]?.color ?? '#999';
  }

  cara(c: TimelineFinding): string {
    return c.surface === 'whole' ? '' : `(${(SURFACE_LABELS[c.surface] ?? c.surface).toLowerCase()})`;
  }
}
