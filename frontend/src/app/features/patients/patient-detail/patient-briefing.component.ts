import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, Input, OnChanges, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../../environments/environment';

interface Dato {
  codigo: string;
  icono: string;
  tono: 'info' | 'alerta' | 'ok' | 'dinero';
  texto: string;
}

/** Ya están en la cabecera de la ficha: no se repiten aquí. */
const EN_CABECERA = new Set(['alergias', 'cita', 'saldo']);

@Component({
  selector: 'app-patient-briefing',
  standalone: true,
  imports: [MatButtonModule, MatIconModule, MatProgressSpinnerModule, MatTooltipModule],
  template: `
    @if (visibles().length || iaDisponible()) {
      <section class="briefing glass-card">
        <header>
          <mat-icon class="sello">assignment_ind</mat-icon>
          <strong>Antes de atender</strong>
          <span class="espacio"></span>
          @if (iaDisponible()) {
            <button mat-stroked-button (click)="resumir()" [disabled]="generando()">
              @if (generando()) { <mat-spinner diameter="16" /> } @else { <mat-icon>auto_awesome</mat-icon> }
              {{ texto() ? 'Volver a resumir' : 'Resumen con IA' }}
            </button>
          }
        </header>

        @if (texto(); as t) {
          <div class="ia">
            <p>{{ t }}</p>
            <footer>
              <span><mat-icon>info</mat-icon>Borrador de IA a partir de los datos del sistema. Revíselo antes de usarlo.</span>
              <button mat-icon-button (click)="copiar(t)" matTooltip="Copiar"><mat-icon>content_copy</mat-icon></button>
            </footer>
          </div>
        }
        @if (error()) { <p class="error">{{ error() }}</p> }

        @if (visibles().length) {
          <ul class="datos">
            @for (d of visibles(); track d.codigo) {
              <li [attr.data-tono]="d.tono"><mat-icon>{{ d.icono }}</mat-icon>{{ d.texto }}</li>
            }
          </ul>
        }
      </section>
    }
  `,
  styles: [
    `
      .briefing { margin: 0 0 14px; padding: 12px 16px; }
      header { display: flex; align-items: center; gap: 8px; strong { font-size: .95rem; } .espacio { flex: 1; }
        .sello { color: var(--color-primary); }
        button mat-spinner { display: inline-block; margin-right: 6px; } }
      .datos { list-style: none; display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0 0; padding: 0; }
      li { display: inline-flex; align-items: center; gap: 6px; padding: 5px 10px; border-radius: 999px; font-size: .8rem;
        background: var(--color-surface-muted); color: var(--color-ink-soft);
        mat-icon { font-size: 16px; width: 16px; height: 16px; }
        &[data-tono='alerta'] { background: var(--color-danger-soft); color: var(--color-danger); }
        &[data-tono='ok'] { background: var(--color-success-soft); color: var(--color-success); }
        &[data-tono='info'] mat-icon { color: var(--color-primary); } }
      .ia { margin-top: 10px; padding: 12px 14px; border-radius: var(--radius-md); background: var(--color-primary-soft);
        p { margin: 0; font-size: .92rem; line-height: 1.5; color: var(--color-ink); }
        footer { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 6px;
          span { display: inline-flex; align-items: center; gap: 4px; font-size: .72rem; color: var(--color-ink-faint); }
          mat-icon { font-size: 14px; width: 14px; height: 14px; } button mat-icon { font-size: 18px; width: 18px; height: 18px; } } }
      .error { margin: 8px 0 0; font-size: .82rem; color: var(--color-danger); }
    `,
  ],
})
export class PatientBriefingComponent implements OnChanges {
  @Input({ required: true }) patientId!: string;

  private readonly http = inject(HttpClient);
  private readonly snack = inject(MatSnackBar);
  readonly datos = signal<Dato[]>([]);
  readonly iaDisponible = signal(false);
  readonly texto = signal<string | null>(null);
  readonly generando = signal(false);
  readonly error = signal<string | null>(null);
  readonly visibles = computed(() => this.datos().filter((d) => !EN_CABECERA.has(d.codigo)));

  async ngOnChanges(): Promise<void> {
    this.texto.set(null);
    this.error.set(null);
    try {
      const r = await firstValueFrom(
        this.http.get<{ datos: Dato[]; ia_disponible: boolean }>(`${environment.apiUrl}/patients/${this.patientId}/briefing`),
      );
      this.datos.set(r.datos);
      this.iaDisponible.set(r.ia_disponible);
    } catch {
      this.datos.set([]);
    }
  }

  async resumir(): Promise<void> {
    this.generando.set(true);
    this.error.set(null);
    try {
      const r = await firstValueFrom(
        this.http.post<{ texto: string }>(`${environment.apiUrl}/patients/${this.patientId}/briefing/ai`, {}),
      );
      this.texto.set(r.texto);
    } catch (e) {
      this.error.set(
        e instanceof HttpErrorResponse && typeof e.error?.detail === 'string' ? e.error.detail : 'No se pudo generar el resumen.',
      );
    } finally {
      this.generando.set(false);
    }
  }

  async copiar(t: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(t);
      this.snack.open('Resumen copiado.', undefined, { duration: 1800 });
    } catch {
      this.snack.open('No se pudo copiar.', undefined, { duration: 1800 });
    }
  }
}
