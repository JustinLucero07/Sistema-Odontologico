import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { firstValueFrom } from 'rxjs';

import { ImportField, PatientImportPreview, PatientImportRow } from '../../core/models/patient.models';
import { PatientsService } from '../../core/services/patients.service';

type Filtro = 'todos' | 'nuevo' | 'duplicado' | 'error';
const MAX_VISTA = 300;

@Component({
  selector: 'app-patient-import-dialog',
  standalone: true,
  imports: [DatePipe, FormsModule, MatButtonModule, MatDialogModule, MatIconModule, MatSelectModule, MatSlideToggleModule],
  template: `
    <h2 mat-dialog-title>Importar pacientes desde Excel</h2>
    <mat-dialog-content>
      @if (resultado(); as r) {
        <div class="hecho">
          <mat-icon>task_alt</mat-icon>
          <strong>Se importaron {{ r.created }} paciente(s)</strong>
          @if (r.skipped) { <span>{{ r.skipped }} se omitieron porque ya existían.</span> }
        </div>
      } @else if (!vista()) {
        <label class="zona" [class.sobre]="arrastrando()"
               (dragover)="$event.preventDefault(); arrastrando.set(true)"
               (dragleave)="arrastrando.set(false)"
               (drop)="soltar($event)">
          <mat-icon>upload_file</mat-icon>
          <strong>{{ leyendo() ? 'Leyendo el archivo…' : 'Arrastra aquí tu archivo o haz clic para elegirlo' }}</strong>
          <span>Excel (.xlsx) o CSV, hasta 5 000 pacientes. Primero verás una vista previa: nada se guarda sin tu confirmación.</span>
          <input type="file" accept=".xlsx,.csv,.txt" (change)="elegir($event)" hidden />
        </label>
        <div class="opciones">
          <label>
            <span>Si el nombre viene en una sola columna, el orden es</span>
            <mat-select [(ngModel)]="orden">
              <mat-option value="nombres_apellidos">Nombres y luego apellidos (ANDREA TATIANA MERINO ARMIJOS)</mat-option>
              <mat-option value="apellidos_nombres">Apellidos y luego nombres (MERINO ARMIJOS ANDREA TATIANA)</mat-option>
            </mat-select>
          </label>
          <button mat-button type="button" (click)="plantilla()"><mat-icon>download</mat-icon>Descargar plantilla</button>
        </div>
        <p class="ayuda">
          Se reconocen columnas como: Nombres, Apellidos (o Nombre completo), Cédula, Teléfono / Celular, WhatsApp, Correo,
          Fecha de nacimiento, Sexo, Dirección, Ciudad, Ocupación y Observaciones. Puedes corregirlas en el siguiente paso.
        </p>
      } @else {
        @let v = vista()!;
        <div class="archivo">
          <mat-icon>description</mat-icon><strong>{{ archivo()?.name }}</strong>
          <button mat-button type="button" (click)="reiniciar()">Cambiar archivo</button>
        </div>

        <div class="cuentas">
          <button type="button" [class.on]="filtro() === 'todos'" (click)="filtro.set('todos')">Todos <strong>{{ v.rows.length }}</strong></button>
          <button type="button" class="nuevo" [class.on]="filtro() === 'nuevo'" (click)="filtro.set('nuevo')">Nuevos <strong>{{ v.counts.nuevo }}</strong></button>
          <button type="button" class="duplicado" [class.on]="filtro() === 'duplicado'" (click)="filtro.set('duplicado')">Ya existen <strong>{{ v.counts.duplicado }}</strong></button>
          <button type="button" class="error" [class.on]="filtro() === 'error'" (click)="filtro.set('error')">Con errores <strong>{{ v.counts.error }}</strong></button>
        </div>

        <details class="columnas" [open]="sinNombre()">
          <summary>Columnas del archivo ({{ reconocidas() }} de {{ v.headers.length }} reconocidas)</summary>
          @if (sinNombre()) {
            <p class="aviso">No se encontró la columna del nombre. Indica cuál es.</p>
          }
          <div class="mapa">
            @for (h of v.headers; track h) {
              <label>
                <span>{{ h }}</span>
                <mat-select [ngModel]="mapa()[h] ?? null" (ngModelChange)="cambiarMapa(h, $event)">
                  <mat-option [value]="null">No importar</mat-option>
                  @for (f of v.fields; track f.code) { <mat-option [value]="f.code">{{ f.label }}</mat-option> }
                </mat-select>
              </label>
            }
          </div>
        </details>

        <div class="tabla">
          <table>
            <thead>
              <tr><th>Fila</th><th>Estado</th><th>Nombres</th><th>Apellidos</th><th>Cédula</th><th>Teléfono</th><th>Correo</th><th>Nacimiento</th></tr>
            </thead>
            <tbody>
              @for (r of filasVista(); track r.row) {
                <tr [attr.data-status]="r.status">
                  <td>{{ r.row }}</td>
                  <td>
                    <span class="tag" [attr.data-status]="r.status">{{ etiqueta[r.status] }}</span>
                    @if (r.errors.length) { <small>{{ r.errors.join(' · ') }}</small> }
                    @if (r.duplicate) { <small>{{ r.duplicate }}</small> }
                  </td>
                  <td>{{ r.data.first_name }}</td>
                  <td>{{ r.data.last_name }}</td>
                  <td>{{ r.data.national_id ?? '—' }}</td>
                  <td>{{ r.data.phone ?? r.data.whatsapp ?? '—' }}</td>
                  <td>{{ r.data.email ?? '—' }}</td>
                  <td>{{ r.data.birth_date ? (r.data.birth_date | date: 'dd/MM/yyyy') : '—' }}</td>
                </tr>
              }
            </tbody>
          </table>
          @if (filtradas().length > filasVista().length) {
            <p class="mas">Se muestran {{ filasVista().length }} de {{ filtradas().length }} filas. Se importarán todas.</p>
          }
        </div>

        @if (v.counts.duplicado) {
          <label class="incluir">
            <mat-slide-toggle [(ngModel)]="incluirRepetidos" />
            <span>Importar también los {{ v.counts.duplicado }} que parecen repetidos (no recomendado)</span>
          </label>
        }
      }
      @if (error()) { <p class="err">{{ error() }}</p> }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      @if (resultado()) {
        <button mat-flat-button type="button" [mat-dialog-close]="true">Listo</button>
      } @else {
        <button mat-button type="button" mat-dialog-close>Cancelar</button>
        @if (vista()) {
          <button mat-flat-button type="button" (click)="importar()" [disabled]="guardando() || aImportar().length === 0">
            {{ guardando() ? 'Importando…' : 'Importar ' + aImportar().length + ' paciente(s)' }}
          </button>
        }
      }
    </mat-dialog-actions>
  `,
  styles: [
    `
      .zona { display: grid; justify-items: center; gap: 6px; padding: 34px 18px; text-align: center; cursor: pointer;
        border: 2px dashed var(--color-border-strong); border-radius: var(--radius-lg); transition: border-color .15s, background .15s;
        mat-icon { font-size: 40px; width: 40px; height: 40px; color: var(--color-primary); }
        span { max-width: 460px; font-size: .82rem; color: var(--color-ink-faint); }
        &:hover, &.sobre { border-color: var(--color-primary); background: var(--color-primary-soft); } }
      .opciones { display: flex; align-items: end; flex-wrap: wrap; gap: 10px; margin-top: 14px;
        label { flex: 1; min-width: 260px; display: grid; gap: 4px; span { font-size: .74rem; font-weight: 600; color: var(--color-ink-soft); } }
        mat-select { padding: 9px 12px; border: 1px solid var(--color-border-strong); border-radius: var(--radius-sm); } }
      .ayuda { font-size: .78rem; color: var(--color-ink-faint); margin: 12px 0 0; }
      .archivo { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; strong { font-size: .9rem; } button { margin-left: auto; } }
      .cuentas { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px;
        button { padding: 6px 12px; border-radius: 999px; border: 1px solid var(--color-border-strong); background: transparent;
          font: inherit; font-size: .8rem; cursor: pointer; color: var(--color-ink-soft); }
        button.on { border-color: var(--color-primary); background: var(--color-primary-soft); color: var(--color-primary); }
        .nuevo strong { color: var(--color-success); } .duplicado strong { color: var(--color-accent); } .error strong { color: var(--color-danger); } }
      .columnas { margin-bottom: 10px; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: var(--radius-md);
        summary { cursor: pointer; font-size: .84rem; font-weight: 600; }
        .aviso { color: var(--color-danger); font-size: .8rem; margin: 8px 0 0; } }
      .mapa { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 8px 12px; margin-top: 10px;
        label { display: grid; gap: 3px; span { font-size: .72rem; font-weight: 600; color: var(--color-ink-soft); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } }
        mat-select { padding: 7px 10px; border: 1px solid var(--color-border-strong); border-radius: var(--radius-sm); font-size: .82rem; } }
      .tabla { max-height: 340px; overflow: auto; border: 1px solid var(--color-border); border-radius: var(--radius-md); }
      table { width: 100%; border-collapse: collapse; font-size: .78rem; }
      th { position: sticky; top: 0; z-index: 1; padding: 7px 8px; text-align: left; background: var(--color-surface-muted); font-size: .68rem; color: var(--color-ink-soft); }
      td { padding: 6px 8px; border-top: 1px solid var(--color-border); vertical-align: top; }
      td small { display: block; margin-top: 2px; color: var(--color-ink-faint); }
      tr[data-status='error'] td small { color: var(--color-danger); }
      .tag { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: .66rem; font-weight: 700;
        &[data-status='nuevo'] { background: var(--color-success-soft); color: var(--color-success); }
        &[data-status='duplicado'] { background: var(--color-accent-soft); color: var(--color-accent); }
        &[data-status='error'] { background: var(--color-danger-soft); color: var(--color-danger); } }
      .mas { margin: 0; padding: 8px; font-size: .76rem; color: var(--color-ink-faint); text-align: center; }
      .incluir { display: flex; align-items: center; gap: 10px; margin-top: 10px; font-size: .82rem; }
      .hecho { display: grid; justify-items: center; gap: 6px; padding: 30px 10px; text-align: center;
        mat-icon { font-size: 44px; width: 44px; height: 44px; color: var(--color-success); } span { color: var(--color-ink-faint); font-size: .84rem; } }
      .err { color: var(--color-danger); font-size: .84rem; margin: 10px 0 0; }
    `,
  ],
})
export class PatientImportDialogComponent {
  private readonly api = inject(PatientsService);

  readonly archivo = signal<File | null>(null);
  readonly vista = signal<PatientImportPreview | null>(null);
  readonly mapa = signal<Record<string, ImportField | null>>({});
  readonly filtro = signal<Filtro>('todos');
  readonly leyendo = signal(false);
  readonly guardando = signal(false);
  readonly arrastrando = signal(false);
  readonly error = signal<string | null>(null);
  readonly resultado = signal<{ created: number; skipped: number } | null>(null);
  orden = 'nombres_apellidos';
  incluirRepetidos = false;

  readonly etiqueta: Record<PatientImportRow['status'], string> = { nuevo: 'Nuevo', duplicado: 'Ya existe', error: 'Error' };

  readonly filtradas = computed(() => {
    const v = this.vista();
    if (!v) return [];
    const f = this.filtro();
    return f === 'todos' ? v.rows : v.rows.filter((r) => r.status === f);
  });
  readonly filasVista = computed(() => this.filtradas().slice(0, MAX_VISTA));
  readonly reconocidas = computed(() => Object.values(this.mapa()).filter(Boolean).length);
  readonly sinNombre = computed(() => {
    const campos = new Set(Object.values(this.mapa()));
    return !campos.has('full_name') && !(campos.has('first_name') && campos.has('last_name'));
  });

  aImportar(): PatientImportRow[] {
    const v = this.vista();
    if (!v) return [];
    return v.rows.filter((r) => r.status === 'nuevo' || (this.incluirRepetidos && r.status === 'duplicado'));
  }

  elegir(ev: Event): void {
    const input = ev.target as HTMLInputElement;
    const f = input.files?.[0];
    input.value = '';
    if (f) void this.leer(f);
  }

  soltar(ev: DragEvent): void {
    ev.preventDefault();
    this.arrastrando.set(false);
    const f = ev.dataTransfer?.files?.[0];
    if (f) void this.leer(f);
  }

  private async leer(f: File, mapping?: Record<string, ImportField | null>): Promise<void> {
    this.archivo.set(f);
    this.leyendo.set(true);
    this.error.set(null);
    try {
      const v = await firstValueFrom(this.api.importPreview(f, this.orden, mapping));
      this.vista.set(v);
      this.mapa.set(v.mapping);
    } catch (e) {
      this.error.set(
        e instanceof HttpErrorResponse && typeof e.error?.detail === 'string'
          ? e.error.detail
          : 'No se pudo leer el archivo. Revise que sea un Excel (.xlsx) o CSV.',
      );
      if (!mapping) this.vista.set(null);
    } finally {
      this.leyendo.set(false);
    }
  }

  cambiarMapa(encabezado: string, campo: ImportField | null): void {
    const m = { ...this.mapa() };
    // Un campo solo puede venir de una columna.
    if (campo) for (const k of Object.keys(m)) if (m[k] === campo) m[k] = null;
    m[encabezado] = campo;
    this.mapa.set(m);
    const f = this.archivo();
    if (f) void this.leer(f, m);
  }

  reiniciar(): void {
    this.vista.set(null);
    this.archivo.set(null);
    this.error.set(null);
  }

  plantilla(): void {
    const csv =
      '﻿Nombres;Apellidos;Cédula;Celular;WhatsApp;Correo;Fecha de nacimiento;Sexo;Dirección;Ciudad;Ocupación;Observaciones\n' +
      'Andrea Tatiana;Merino Armijos;0105555555;0987654321;0987654321;andrea@correo.ec;15/03/1998;F;Av. Loja 1-23;Cuenca;Estudiante;\n';
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = 'plantilla-pacientes.csv';
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 30_000);
  }

  async importar(): Promise<void> {
    const filas = this.aImportar();
    if (!filas.length) return;
    this.guardando.set(true);
    this.error.set(null);
    try {
      this.resultado.set(
        await firstValueFrom(this.api.importConfirm(filas.map((r) => r.data), !this.incluirRepetidos)),
      );
    } catch (e) {
      this.error.set(
        e instanceof HttpErrorResponse && typeof e.error?.detail === 'string'
          ? e.error.detail
          : 'No se pudo importar. Revise las filas con errores e intente de nuevo.',
      );
    } finally {
      this.guardando.set(false);
    }
  }
}

export function openPatientImportDialog(dialog: MatDialog): Promise<boolean | undefined> {
  const ref = dialog.open(PatientImportDialogComponent, {
    width: '980px',
    maxWidth: '96vw',
    panelClass: 'app-dialog',
    autoFocus: false,
  });
  return firstValueFrom(ref.afterClosed());
}
