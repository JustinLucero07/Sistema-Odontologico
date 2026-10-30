import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { formatMoney } from '../../core/models/finance.models';
import { INVOICE_STATUS_LABELS, Invoice } from '../../core/models/invoicing.models';
import { InvoicingService } from '../../core/services/invoicing.service';
import { promptText } from '../confirm-dialog/prompt-dialog.component';

@Component({
  selector: 'app-invoice-detail-dialog',
  standalone: true,
  imports: [DatePipe, FormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatIconModule, MatInputModule],
  template: `
    @if (inv(); as f) {
      <h2 mat-dialog-title>
        {{ f.doc_type === '01' ? 'Factura' : 'Nota de crédito' }} {{ f.number }}
        <span class="status" [attr.data-status]="f.status">{{ labels[f.status] }}</span>
      </h2>
      <mat-dialog-content>
        @if (f.environment === '1') {
          <p class="tag">Ambiente de pruebas: sin validez tributaria</p>
        }
        <dl class="grid">
          <dt>Comprador</dt><dd>{{ f.buyer_name }} · {{ f.buyer_id }}</dd>
          <dt>Emitida</dt><dd>{{ f.issue_date | date: 'dd/MM/yyyy' }}</dd>
          @if (f.authorized_at) { <dt>Autorizada</dt><dd>{{ f.authorized_at | date: 'dd/MM/yyyy HH:mm' }}</dd> }
          <dt>Clave de acceso</dt><dd class="key">{{ f.access_key }}</dd>
          @if (f.reason) { <dt>Motivo</dt><dd>{{ f.reason }}</dd> }
          @if (f.buyer_email) { <dt>Correo</dt><dd>{{ f.buyer_email }}{{ f.emailed_at ? ' · enviado' : '' }}</dd> }
          @if (f.discard_reason) { <dt>Descartada</dt><dd>{{ f.discard_reason }}</dd> }
        </dl>

        <table class="lines">
          <thead><tr><th>Concepto</th><th>Cant.</th><th>IVA</th><th class="num">Subtotal</th></tr></thead>
          <tbody>
            @for (l of f.lines; track l.id) {
              <tr><td>{{ l.description }}</td><td>{{ +l.quantity }}</td><td>{{ +l.vat_rate }} %</td><td class="num">$ {{ money(l.subtotal) }}</td></tr>
            }
          </tbody>
          <tfoot>
            <tr><td colspan="3">Subtotal</td><td class="num">$ {{ money(f.subtotal) }}</td></tr>
            <tr><td colspan="3">IVA</td><td class="num">$ {{ money(f.vat) }}</td></tr>
            <tr class="total"><td colspan="3">Total</td><td class="num">$ {{ money(f.total) }}</td></tr>
            @if (+f.credited > 0) {
              <tr><td colspan="3">Notas de crédito</td><td class="num">− $ {{ money(f.credited) }}</td></tr>
            }
          </tfoot>
        </table>

        @if (f.sri_messages.length && f.status !== 'autorizada') {
          <div class="sri">
            <strong>Respuesta del SRI</strong>
            @for (m of f.sri_messages; track $index) {
              <p><b>{{ m.identificador }}</b> {{ m.mensaje }} @if (m.informacion) { <span>— {{ m.informacion }}</span> }</p>
            }
          </div>
        }
        @if (f.last_error && (f.status === 'pendiente' || f.status === 'recibida' || f.status === 'autorizada')) {
          <p class="hint"><mat-icon>schedule</mat-icon>{{ f.last_error }}
            @if (f.next_attempt_at && f.status !== 'autorizada') { · próximo intento {{ f.next_attempt_at | date: 'HH:mm' }} }
          </p>
        }

        @if (creditOpen()) {
          <div class="credit">
            <strong>Nota de crédito</strong>
            <p class="hint">Disponible para acreditar: $ {{ money(available()) }}. Deje el monto vacío para anular la factura completa.</p>
            <div class="row">
              <mat-form-field appearance="outline" subscriptSizing="dynamic" class="grow">
                <mat-label>Motivo</mat-label>
                <input matInput [(ngModel)]="creditReason" maxlength="300" />
              </mat-form-field>
              <mat-form-field appearance="outline" subscriptSizing="dynamic">
                <mat-label>Monto con IVA (opcional)</mat-label>
                <span matTextPrefix>$&nbsp;</span>
                <input matInput type="number" min="0" step="0.01" [(ngModel)]="creditAmount" />
              </mat-form-field>
              <button mat-flat-button class="danger" (click)="issueCredit()" [disabled]="busy() || creditReason.trim().length < 3">Emitir</button>
            </div>
          </div>
        }
      </mat-dialog-content>
      <mat-dialog-actions>
        <button mat-button (click)="openPdf()"><mat-icon>picture_as_pdf</mat-icon>PDF</button>
        @if (f.status === 'autorizada') {
          <button mat-button (click)="downloadXml()"><mat-icon>code</mat-icon>XML</button>
          @if (canWrite) {
            <button mat-button (click)="sendEmail()" [disabled]="busy()"><mat-icon>mail</mat-icon>Correo</button>
          }
          @if (f.buyer_phone) {
            <a mat-button [href]="whatsapp()" target="_blank" rel="noopener"><mat-icon>chat</mat-icon>WhatsApp</a>
          }
        }
        <span class="spacer"></span>
        @if (canWrite) {
          @if (f.status === 'devuelta' || f.status === 'no_autorizada' || f.status === 'pendiente' || f.status === 'recibida') {
            <button mat-stroked-button (click)="retry()" [disabled]="busy()"><mat-icon>sync</mat-icon>{{ f.status === 'recibida' ? 'Consultar SRI' : 'Reintentar' }}</button>
          }
          @if (f.status === 'devuelta' || f.status === 'no_autorizada') {
            <button mat-button class="danger-text" (click)="discard()" [disabled]="busy()">Descartar</button>
          }
          @if (f.doc_type === '01' && f.status === 'autorizada' && available() > 0) {
            <button mat-stroked-button (click)="creditOpen.set(!creditOpen())"><mat-icon>undo</mat-icon>Nota de crédito</button>
          }
        }
        <button mat-flat-button mat-dialog-close>Cerrar</button>
      </mat-dialog-actions>
    }
  `,
  styles: [
    `
      h2 { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
      .status { font-size: 0.72rem; font-weight: 700; padding: 3px 10px; border-radius: 999px; background: color-mix(in srgb, #8a9598 18%, transparent); }
      .status[data-status='autorizada'] { background: color-mix(in srgb, #2b9a5b 16%, transparent); color: #1f7a45; }
      .status[data-status='devuelta'], .status[data-status='no_autorizada'] { background: color-mix(in srgb, #d0453a 14%, transparent); color: #b3352b; }
      .status[data-status='pendiente'], .status[data-status='recibida'] { background: color-mix(in srgb, #c98a1e 16%, transparent); color: #8a5d12; }
      .tag { display: inline-block; margin: 0 0 8px; padding: 3px 10px; border-radius: 8px; font-size: 0.78rem; background: color-mix(in srgb, #c98a1e 14%, transparent); }
      .grid { display: grid; grid-template-columns: 140px 1fr; gap: 4px 12px; margin: 0 0 12px; font-size: 0.9rem; }
      dt { color: var(--color-ink-faint); }
      dd { margin: 0; }
      .key { font-family: ui-monospace, monospace; font-size: 0.78rem; word-break: break-all; }
      .lines { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
      .lines th, .lines td { padding: 6px 4px; border-bottom: 1px solid var(--color-border); text-align: left; }
      .num { text-align: right !important; font-variant-numeric: tabular-nums; }
      tfoot td { border-bottom: 0 !important; }
      .total td { font-weight: 800; font-size: 1rem; }
      .sri { margin-top: 12px; padding: 10px 12px; border-radius: 12px; background: color-mix(in srgb, #d0453a 8%, transparent); font-size: 0.86rem; }
      .sri p { margin: 4px 0 0; }
      .hint { display: flex; align-items: center; gap: 6px; color: var(--color-ink-faint); font-size: 0.84rem; }
      .credit { margin-top: 14px; padding: 12px; border: 1px solid var(--color-border); border-radius: 14px; }
      .credit .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
      .grow { flex: 1; min-width: 200px; }
      .spacer { flex: 1; }
      .danger { --mdc-filled-button-container-color: var(--color-danger, #b3352b); --mdc-filled-button-label-text-color: #fff; }
      .danger-text { color: var(--color-danger, #b3352b); }
      mat-dialog-actions { flex-wrap: wrap; gap: 4px; }
    `,
  ],
})
export class InvoiceDetailDialogComponent implements OnInit {
  private readonly data = inject<{ id: string }>(MAT_DIALOG_DATA);
  private readonly service = inject(InvoicingService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly auth = inject(AuthService);

  readonly money = formatMoney;
  readonly labels = INVOICE_STATUS_LABELS;
  readonly canWrite = this.auth.hasPermission('invoices:write');
  readonly inv = signal<Invoice | null>(null);
  readonly busy = signal(false);
  readonly creditOpen = signal(false);
  readonly available = computed(() => {
    const f = this.inv();
    return f ? Math.round((+f.total - +f.credited) * 100) / 100 : 0;
  });
  creditReason = '';
  creditAmount: number | null = null;

  async ngOnInit(): Promise<void> {
    this.inv.set(await firstValueFrom(this.service.get(this.data.id)));
  }

  private report(err: unknown, fallback: string): void {
    const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
    this.snackBar.open(typeof detail === 'string' ? detail : fallback, 'Cerrar', { duration: 7000 });
  }

  private async run(action: () => Promise<Invoice>, ok?: string): Promise<void> {
    this.busy.set(true);
    try {
      this.inv.set(await action());
      if (ok) this.snackBar.open(ok, 'Cerrar', { duration: 3000 });
    } catch (err) {
      this.report(err, 'No se pudo completar la operación.');
    } finally {
      this.busy.set(false);
    }
  }

  retry(): Promise<void> {
    return this.run(() => firstValueFrom(this.service.retry(this.data.id)));
  }

  async discard(): Promise<void> {
    const reason = await promptText(this.dialog, {
      title: 'Descartar comprobante',
      message: 'El SRI no lo aceptó. Al descartarlo deja de contar como factura y sus cargos quedan libres para facturar de nuevo.',
      label: 'Motivo',
      minLength: 3,
      multiline: true,
      confirmLabel: 'Descartar',
      danger: true,
    });
    if (reason) await this.run(() => firstValueFrom(this.service.discard(this.data.id, reason)), 'Comprobante descartado');
  }

  async issueCredit(): Promise<void> {
    const amount = this.creditAmount && this.creditAmount > 0 ? this.creditAmount.toFixed(2) : null;
    this.busy.set(true);
    try {
      const nota = await firstValueFrom(this.service.creditNote(this.data.id, this.creditReason.trim(), amount));
      this.snackBar.open(
        nota.status === 'autorizada' ? `Nota de crédito ${nota.number} autorizada` : `Nota de crédito ${nota.number}: ${this.labels[nota.status]}`,
        'Cerrar',
        { duration: 5000 },
      );
      this.creditOpen.set(false);
      this.inv.set(await firstValueFrom(this.service.get(this.data.id)));
    } catch (err) {
      this.report(err, 'No se pudo emitir la nota de crédito.');
    } finally {
      this.busy.set(false);
    }
  }

  async sendEmail(): Promise<void> {
    const f = this.inv();
    if (!f) return;
    const email = await promptText(this.dialog, {
      title: 'Enviar por correo',
      label: 'Correo',
      initial: f.buyer_email ?? '',
      minLength: 5,
      confirmLabel: 'Enviar',
    });
    if (email) await this.run(() => firstValueFrom(this.service.email(this.data.id, email)), 'Enviada por correo');
  }

  async openPdf(): Promise<void> {
    try {
      const blob = await firstValueFrom(this.service.pdf(this.data.id));
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank', 'noopener');
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      this.report(err, 'No se pudo abrir el PDF.');
    }
  }

  async downloadXml(): Promise<void> {
    const f = this.inv();
    if (!f) return;
    const blob = await firstValueFrom(this.service.xml(f.id));
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${f.doc_type === '01' ? 'factura' : 'nota-credito'}-${f.number}.xml`;
    link.click();
    URL.revokeObjectURL(url);
  }

  whatsapp(): string {
    const f = this.inv();
    if (!f?.buyer_phone) return '';
    let n = f.buyer_phone.replace(/\D/g, '');
    if (n.length === 10 && n.startsWith('0')) n = '593' + n.slice(1);
    const tipo = f.doc_type === '01' ? 'factura' : 'nota de crédito';
    const texto = `Hola ${f.buyer_name}, su ${tipo} electrónica ${f.number} por $${this.money(f.total)} fue autorizada por el SRI. Clave de acceso: ${f.access_key}`;
    return `https://wa.me/${n}?text=${encodeURIComponent(texto)}`;
  }
}

export function openInvoiceDetail(dialog: MatDialog, id: string): Promise<void> {
  return firstValueFrom(
    dialog
      .open(InvoiceDetailDialogComponent, { data: { id }, width: '720px', maxWidth: '96vw', panelClass: 'app-dialog' })
      .afterClosed(),
  );
}
