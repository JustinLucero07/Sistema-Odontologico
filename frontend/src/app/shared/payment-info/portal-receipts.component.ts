import { DatePipe } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, EventEmitter, Input, OnChanges, OnDestroy, Output, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';
import { formatMoney } from '../../core/models/finance.models';

export interface Comprobante {
  id: string;
  patient_id: string;
  patient_name: string | null;
  amount: string;
  paid_on: string;
  reference: string | null;
  note: string | null;
  destino: string;
  status: 'pendiente' | 'aceptado' | 'rechazado';
  status_label: string;
  reject_reason: string | null;
  payment_id: string | null;
  mime_type: string;
  created_at: string;
  reviewed_at: string | null;
}

const API = environment.apiUrl;

function detalle(e: unknown, defecto: string): string {
  return e instanceof HttpErrorResponse && typeof e.error?.detail === 'string' ? e.error.detail : defecto;
}

@Component({
  selector: 'app-review-receipt-dialog',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatDialogModule, MatIconModule],
  template: `
    <h2 mat-dialog-title>Revisar comprobante</h2>
    <mat-dialog-content>
      <div class="archivo">
        @if (url(); as u) {
          @if (c.mime_type === 'application/pdf') {
            <a mat-stroked-button [href]="u" target="_blank" rel="noopener"><mat-icon>picture_as_pdf</mat-icon>Abrir PDF</a>
          } @else {
            <a [href]="u" target="_blank" rel="noopener"><img [src]="u" alt="Comprobante enviado por el paciente" /></a>
          }
        } @else {
          <span class="cargando">Cargando archivo…</span>
        }
      </div>
      <dl>
        @if (c.patient_name) { <div><dt>Paciente</dt><dd>{{ c.patient_name }}</dd></div> }
        <div><dt>Para</dt><dd>{{ c.destino }}</dd></div>
        <div><dt>Fecha del pago</dt><dd>{{ c.paid_on | date: 'dd/MM/yyyy' }}</dd></div>
        <div><dt>Referencia</dt><dd>{{ c.reference || '—' }}</dd></div>
        @if (c.note) { <div class="full"><dt>Nota del paciente</dt><dd>{{ c.note }}</dd></div> }
      </dl>

      @if (!rechazando()) {
        <div class="campos">
          <label>Monto a registrar ($)
            <input inputmode="decimal" [value]="monto()" (input)="monto.set($any($event.target).value)" />
          </label>
          <label>Medio
            <select [value]="metodo()" (change)="metodo.set($any($event.target).value)">
              <option value="transferencia">Transferencia bancaria</option>
              <option value="deposito">Depósito bancario</option>
            </select>
          </label>
        </div>
        <p class="ayuda">Al aceptar se registra el pago y el saldo del paciente se actualiza al instante.</p>
      } @else {
        <label class="motivo">Motivo del rechazo (el paciente lo verá)
          <textarea rows="3" [value]="motivo()" (input)="motivo.set($any($event.target).value)"
                    placeholder="Ej.: No se ve el monto, la transferencia no llegó…"></textarea>
        </label>
      }
      @if (error(); as e) { <p class="error">{{ e }}</p> }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      @if (!rechazando()) {
        <button mat-button class="rojo" (click)="rechazando.set(true)" [disabled]="ocupado()">Rechazar</button>
        <button mat-flat-button (click)="aceptar()" [disabled]="ocupado()"><mat-icon>check</mat-icon>Aceptar y registrar pago</button>
      } @else {
        <button mat-button (click)="rechazando.set(false)" [disabled]="ocupado()">Volver</button>
        <button mat-flat-button class="peligro" (click)="rechazar()" [disabled]="ocupado() || motivo().trim().length < 3">Rechazar comprobante</button>
      }
    </mat-dialog-actions>
  `,
  styles: [
    `
      .archivo { display: grid; place-items: center; min-height: 120px; margin-bottom: 12px; border-radius: 12px;
        background: var(--color-surface-muted); overflow: hidden;
        img { max-width: 100%; max-height: 46vh; object-fit: contain; display: block; } }
      .cargando { font-size: .85rem; color: var(--color-ink-faint); }
      dl { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; margin: 0 0 12px;
        dt { font-size: .72rem; color: var(--color-ink-faint); } dd { margin: 0; font-size: .9rem; } .full { grid-column: 1 / -1; } }
      .campos { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
      label { display: grid; gap: 4px; font-size: .76rem; font-weight: 600; color: var(--color-ink-soft); }
      input, select, textarea { font: inherit; font-size: .92rem; padding: 9px 11px; border: 1px solid var(--color-border-strong);
        border-radius: 10px; background: var(--color-surface); color: var(--color-ink);
        &:focus { outline: none; border-color: var(--color-primary); } }
      .ayuda { margin: 8px 0 0; font-size: .76rem; color: var(--color-ink-faint); }
      .error { margin: 8px 0 0; color: var(--color-danger); font-size: .84rem; }
      .rojo { color: var(--color-danger); }
      .peligro { --mdc-filled-button-container-color: var(--color-danger); --mdc-filled-button-label-text-color: #fff; }
    `,
  ],
})
export class ReviewReceiptDialogComponent implements OnDestroy {
  readonly c = inject<Comprobante>(MAT_DIALOG_DATA);
  private readonly http = inject(HttpClient);
  private readonly ref = inject(MatDialogRef<ReviewReceiptDialogComponent, boolean>);
  readonly url = signal<string | null>(null);
  readonly monto = signal(this.c.amount);
  readonly metodo = signal('transferencia');
  readonly motivo = signal('');
  readonly rechazando = signal(false);
  readonly ocupado = signal(false);
  readonly error = signal<string | null>(null);

  constructor() {
    void this.cargarArchivo();
  }

  ngOnDestroy(): void {
    const u = this.url();
    if (u) URL.revokeObjectURL(u);
  }

  private async cargarArchivo(): Promise<void> {
    try {
      const blob = await firstValueFrom(this.http.get(`${API}/portal-receipts/${this.c.id}/file`, { responseType: 'blob' }));
      this.url.set(URL.createObjectURL(blob));
    } catch {
      this.error.set('No se pudo cargar el archivo.');
    }
  }

  async aceptar(): Promise<void> {
    const monto = Number(String(this.monto()).replace(',', '.'));
    if (!(monto > 0)) return this.error.set('Escriba un monto válido.');
    await this.hacer(`${API}/portal-receipts/${this.c.id}/accept`, { amount: monto.toFixed(2), method: this.metodo() });
  }

  async rechazar(): Promise<void> {
    await this.hacer(`${API}/portal-receipts/${this.c.id}/reject`, { reason: this.motivo().trim() });
  }

  private async hacer(url: string, body: object): Promise<void> {
    this.ocupado.set(true);
    this.error.set(null);
    try {
      await firstValueFrom(this.http.post(url, body));
      this.ref.close(true);
    } catch (e) {
      this.error.set(detalle(e, 'No se pudo completar.'));
    } finally {
      this.ocupado.set(false);
    }
  }
}

export async function revisarComprobante(dialog: MatDialog, c: Comprobante): Promise<boolean> {
  const ref = dialog.open(ReviewReceiptDialogComponent, { data: c, width: '520px', maxWidth: '94vw', panelClass: 'app-dialog' });
  return (await firstValueFrom(ref.afterClosed())) === true;
}

@Component({
  selector: 'app-portal-receipts',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatIconModule, RouterLink],
  template: `
    @if (items().length) {
      <section class="recibos glass-card">
        <header>
          <mat-icon>receipt</mat-icon>
          <div>
            <h3>{{ patientId ? 'Comprobantes enviados desde el portal' : 'Comprobantes por revisar' }}</h3>
            <p>El paciente subió su transferencia. Revísela y acéptela para registrar el pago.</p>
          </div>
        </header>
        @for (c of items(); track c.id) {
          <div class="fila">
            <div class="info">
              <strong class="numeric">$ {{ money(c.amount) }}</strong>
              <span>
                @if (!patientId && c.patient_name) { <a [routerLink]="['/patients', c.patient_id]">{{ c.patient_name }}</a> · }
                {{ c.destino }} · pagado el {{ c.paid_on | date: 'dd/MM/yyyy' }}
              </span>
              @if (c.reject_reason) { <em>Rechazado: {{ c.reject_reason }}</em> }
            </div>
            @if (c.status === 'pendiente' && canWrite) {
              <button mat-flat-button (click)="revisar(c)"><mat-icon>fact_check</mat-icon>Revisar</button>
            } @else {
              <span class="estado" [attr.data-estado]="c.status">{{ c.status_label }}</span>
            }
          </div>
        }
      </section>
    }
  `,
  styles: [
    `
      .recibos { padding: 14px 18px; margin-bottom: 14px; border-left: 3px solid var(--color-accent); }
      header { display: flex; gap: 10px; align-items: flex-start; margin-bottom: 6px;
        > mat-icon { color: var(--color-accent); }
        h3 { margin: 0; font-size: .95rem; } p { margin: 2px 0 0; font-size: .78rem; color: var(--color-ink-faint); } }
      .fila { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 9px 0; border-top: 1px solid var(--color-border); }
      .info { display: grid; line-height: 1.35; min-width: 0;
        span { font-size: .8rem; color: var(--color-ink-soft); } em { font-size: .78rem; color: var(--color-danger); font-style: normal; }
        a { color: var(--color-ink); font-weight: 600; text-decoration: none; &:hover { color: var(--color-primary); } } }
      .estado { flex-shrink: 0; padding: 3px 10px; border-radius: 999px; font-size: .72rem; font-weight: 600;
        background: var(--color-surface-muted); color: var(--color-ink-soft);
        &[data-estado='aceptado'] { background: var(--color-success-soft); color: var(--color-success); }
        &[data-estado='rechazado'] { background: var(--color-danger-soft); color: var(--color-danger); } }
    `,
  ],
})
export class PortalReceiptsComponent implements OnChanges {
  @Input() patientId: string | null = null;
  @Input() canWrite = false;
  @Output() changed = new EventEmitter<void>();

  private readonly http = inject(HttpClient);
  private readonly dialog = inject(MatDialog);
  private readonly snack = inject(MatSnackBar);
  readonly items = signal<Comprobante[]>([]);
  readonly money = formatMoney;

  async ngOnChanges(): Promise<void> {
    await this.cargar();
  }

  async cargar(): Promise<void> {
    const url = this.patientId ? `${API}/patients/${this.patientId}/portal-receipts` : `${API}/portal-receipts/pending`;
    try {
      const todos = await firstValueFrom(this.http.get<Comprobante[]>(url));
      const pendientes = todos.filter((c) => c.status === 'pendiente');
      this.items.set([...pendientes, ...todos.filter((c) => c.status !== 'pendiente').slice(0, 3)]);
    } catch {
      this.items.set([]);
    }
  }

  async revisar(c: Comprobante): Promise<void> {
    if (await revisarComprobante(this.dialog, c)) {
      this.snack.open('Comprobante revisado', undefined, { duration: 2500 });
      await this.cargar();
      this.changed.emit();
    }
  }
}

@Component({
  selector: 'app-pending-receipts-dialog',
  standalone: true,
  imports: [MatButtonModule, MatDialogModule, PortalReceiptsComponent],
  template: `
    <h2 mat-dialog-title>Comprobantes por revisar</h2>
    <mat-dialog-content>
      <app-portal-receipts [canWrite]="data.canWrite" />
    </mat-dialog-content>
    <mat-dialog-actions align="end"><button mat-button mat-dialog-close>Cerrar</button></mat-dialog-actions>
  `,
})
export class PendingReceiptsDialogComponent {
  readonly data = inject<{ canWrite: boolean }>(MAT_DIALOG_DATA);
}

export async function abrirComprobantesPendientes(dialog: MatDialog, canWrite: boolean): Promise<void> {
  const ref = dialog.open(PendingReceiptsDialogComponent, { data: { canWrite }, width: '640px', maxWidth: '94vw', panelClass: 'app-dialog' });
  await firstValueFrom(ref.afterClosed());
}
