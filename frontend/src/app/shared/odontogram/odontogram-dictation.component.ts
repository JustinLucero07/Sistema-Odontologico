import { HttpClient } from '@angular/common/http';
import { Component, EventEmitter, NgZone, OnDestroy, Output, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { Subject, debounceTime, firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';
import { SURFACE_LABELS, TOOTH_CONDITION_BY_CODE } from './tooth-conditions';

export interface HallazgoDictado {
  fdi_number: string;
  surface: string;
  condition: string;
}

type Reconocedor = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start(): void;
  stop(): void;
  onresult: ((e: { resultIndex: number; results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }> }) => void) | null;
  onend: (() => void) | null;
  onerror: ((e: { error: string }) => void) | null;
};

@Component({
  selector: 'app-odontogram-dictation',
  standalone: true,
  imports: [FormsModule, MatButtonModule, MatIconModule],
  template: `
    <section class="dictado glass-card">
      <header>
        <h3><mat-icon>mic</mat-icon>Dictar hallazgos</h3>
        <button mat-icon-button (click)="cerrar.emit()" aria-label="Cerrar"><mat-icon>close</mat-icon></button>
      </header>
      <p class="ayuda">
        Ej.: <em>«pieza 36 caries oclusal, 11 corona, 46 mesial y distal restauración, falta el 18»</em>.
        Separe cada pieza con una pausa o una coma.
      </p>

      <div class="entrada">
        @if (soportado) {
          <button type="button" class="mic" [class.on]="escuchando()" (click)="alternar()" [attr.aria-label]="escuchando() ? 'Detener' : 'Hablar'">
            <mat-icon>{{ escuchando() ? 'stop' : 'mic' }}</mat-icon>
          </button>
        }
        <textarea
          rows="3"
          [ngModel]="texto()"
          (ngModelChange)="escribir($event)"
          [placeholder]="soportado ? 'Toque el micrófono y hable, o escriba aquí…' : 'Escriba aquí (este navegador no permite dictar; use Chrome o Edge)…'"
        ></textarea>
      </div>
      @if (escuchando()) { <p class="vivo"><span class="punto"></span>Escuchando… {{ parcial() }}</p> }
      @if (error()) { <p class="error">{{ error() }}</p> }

      @if (hallazgos().length || sinEntender().length) {
        <div class="resultado">
          @if (hallazgos().length) {
            <span class="titulo">Se registrará:</span>
            @for (h of hallazgos(); track $index) {
              <span class="chip"><i [style.background]="color(h)"></i>{{ h.fdi_number }} · {{ etiqueta(h) }}{{ h.surface === 'whole' ? '' : ' · ' + cara(h) }}</span>
            }
          }
          @if (sinEntender().length) {
            <p class="no">No entendí: {{ sinEntender().join(' · ') }}</p>
          }
        </div>
      }
      <footer>
        <button mat-button (click)="limpiar()" [disabled]="!texto()">Borrar</button>
        <button mat-flat-button (click)="aplicarTodo()" [disabled]="!hallazgos().length">
          <mat-icon>check</mat-icon>Aplicar {{ hallazgos().length || '' }} al odontograma
        </button>
      </footer>
    </section>
  `,
  styles: [
    `
      .dictado { padding: 14px 18px; margin-bottom: 14px; }
      header { display: flex; align-items: center; justify-content: space-between;
        h3 { display: flex; align-items: center; gap: 8px; margin: 0; font-size: 1rem; mat-icon { color: var(--color-primary); } } }
      .ayuda { margin: 2px 0 10px; font-size: .78rem; color: var(--color-ink-faint); }
      .entrada { display: flex; gap: 10px; align-items: flex-start; }
      textarea { flex: 1; padding: 10px 12px; border: 1px solid var(--color-border-strong); border-radius: var(--radius-md);
        background: var(--color-surface); font: inherit; font-size: .9rem; color: var(--color-ink); resize: vertical;
        &:focus { outline: none; border-color: var(--color-primary); } }
      .mic { display: grid; place-items: center; width: 56px; height: 56px; border: 0; border-radius: 50%; cursor: pointer; flex-shrink: 0;
        background: var(--color-primary); color: var(--color-on-primary); box-shadow: 0 8px 20px -10px var(--color-primary);
        mat-icon { font-size: 28px; width: 28px; height: 28px; }
        &.on { background: var(--color-danger); animation: latido 1.2s ease-in-out infinite; } }
      @keyframes latido { 50% { box-shadow: 0 0 0 10px color-mix(in srgb, var(--color-danger) 20%, transparent); } }
      .vivo { display: flex; align-items: center; gap: 6px; margin: 8px 0 0; font-size: .8rem; color: var(--color-ink-soft);
        .punto { width: 8px; height: 8px; border-radius: 50%; background: var(--color-danger); } }
      .error { margin: 8px 0 0; font-size: .82rem; color: var(--color-danger); }
      .resultado { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 12px;
        .titulo { font-size: .78rem; font-weight: 600; color: var(--color-ink-soft); }
        .no { flex-basis: 100%; margin: 4px 0 0; font-size: .78rem; color: var(--color-accent); } }
      .chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; font-size: .78rem; font-weight: 600;
        background: var(--color-surface-muted); i { width: 9px; height: 9px; border-radius: 3px; } }
      footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
      @media (prefers-reduced-motion: reduce) { .mic.on { animation: none; } }
    `,
  ],
})
export class OdontogramDictationComponent implements OnDestroy {
  @Output() aplicar = new EventEmitter<HallazgoDictado[]>();
  @Output() cerrar = new EventEmitter<void>();

  private readonly http = inject(HttpClient);
  private readonly zone = inject(NgZone);
  private readonly cambios = new Subject<string>();
  private reconocedor: Reconocedor | null = null;

  readonly soportado = !!((window as unknown as Record<string, unknown>)['SpeechRecognition'] || (window as unknown as Record<string, unknown>)['webkitSpeechRecognition']);
  readonly texto = signal('');
  readonly parcial = signal('');
  readonly escuchando = signal(false);
  readonly error = signal<string | null>(null);
  readonly hallazgos = signal<HallazgoDictado[]>([]);
  readonly sinEntender = signal<string[]>([]);

  constructor() {
    this.cambios.pipe(debounceTime(350)).subscribe((t) => void this.interpretar(t));
  }

  ngOnDestroy(): void {
    this.reconocedor?.stop();
  }

  escribir(t: string): void {
    this.texto.set(t);
    this.cambios.next(t);
  }

  alternar(): void {
    if (this.escuchando()) {
      this.reconocedor?.stop();
      return;
    }
    const w = window as unknown as Record<string, new () => Reconocedor>;
    const R = w['SpeechRecognition'] || w['webkitSpeechRecognition'];
    if (!R) return;
    const r = new R();
    r.lang = 'es-EC';
    r.continuous = true;
    r.interimResults = true;
    r.onresult = (e) => {
      this.zone.run(() => {
        let final = '';
        let parcial = '';
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const x = e.results[i];
          if (x.isFinal) final += x[0].transcript;
          else parcial += x[0].transcript;
        }
        this.parcial.set(parcial);
        if (final.trim()) {
          // Cada frase terminada se agrega como un trozo aparte (con coma).
          const nuevo = [this.texto().trim(), final.trim()].filter(Boolean).join(', ');
          this.escribir(nuevo);
        }
      });
    };
    r.onerror = (e) =>
      this.zone.run(() =>
        this.error.set(
          e.error === 'not-allowed'
            ? 'El navegador no tiene permiso para usar el micrófono.'
            : e.error === 'no-speech'
              ? 'No se escuchó nada. Intente de nuevo.'
              : 'No se pudo usar el micrófono.',
        ),
      );
    r.onend = () => this.zone.run(() => {
      this.escuchando.set(false);
      this.parcial.set('');
    });
    this.error.set(null);
    this.reconocedor = r;
    r.start();
    this.escuchando.set(true);
  }

  private async interpretar(t: string): Promise<void> {
    if (!t.trim()) {
      this.hallazgos.set([]);
      this.sinEntender.set([]);
      return;
    }
    try {
      const r = await firstValueFrom(
        this.http.post<{ hallazgos: HallazgoDictado[]; sin_entender: string[] }>(`${environment.apiUrl}/odontogram/dictation`, { texto: t }),
      );
      this.hallazgos.set(r.hallazgos);
      this.sinEntender.set(r.sin_entender);
    } catch {
      this.error.set('No se pudo interpretar el dictado.');
    }
  }

  aplicarTodo(): void {
    this.aplicar.emit(this.hallazgos());
    this.limpiar();
  }

  limpiar(): void {
    this.texto.set('');
    this.hallazgos.set([]);
    this.sinEntender.set([]);
  }

  etiqueta(h: HallazgoDictado): string {
    return TOOTH_CONDITION_BY_CODE[h.condition]?.label ?? h.condition;
  }

  color(h: HallazgoDictado): string {
    return TOOTH_CONDITION_BY_CODE[h.condition]?.color ?? '#999';
  }

  cara(h: HallazgoDictado): string {
    return (SURFACE_LABELS[h.surface] ?? h.surface).toLowerCase();
  }
}
