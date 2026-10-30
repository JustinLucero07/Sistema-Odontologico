import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { firstValueFrom } from 'rxjs';

import { formatMoney } from '../../core/models/finance.models';
import {
  Invoice,
  InvoiceCreate,
  InvoiceableCharge,
  InvoicingCatalogs,
  InvoicingSettings,
} from '../../core/models/invoicing.models';
import { PatientListItem } from '../../core/models/patient.models';
import { InvoicingService } from '../../core/services/invoicing.service';
import { PatientPickerComponent } from '../patient-picker/patient-picker.component';

export interface InvoiceCreateData {
  patientId?: string | null;
  patientName?: string | null;
}

interface ChargeRow extends InvoiceableCharge {
  selected: boolean;
  vat_code: string;
}

interface ManualRow {
  description: string;
  quantity: number;
  price: number;
  vat_code: string;
}

type BuyerMode = 'paciente' | 'otro' | 'final';

/** Separa el IVA de un precio que ya lo incluye, igual que el servidor. */
function split(total: number, rate: number): { base: number; vat: number } {
  const r2 = (n: number) => Math.round(n * 100) / 100;
  const base = rate ? r2(total / (1 + rate / 100)) : r2(total);
  return { base, vat: r2((base * rate) / 100) };
}

@Component({
  selector: 'app-invoice-create-dialog',
  standalone: true,
  imports: [
    DatePipe,
    FormsModule,
    MatButtonModule,
    MatCheckboxModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    PatientPickerComponent,
  ],
  template: `
    <h2 mat-dialog-title>Nueva factura</h2>
    <mat-dialog-content>
      @if (settings(); as s) {
        @if (s.missing.length) {
          <div class="notice bad">
            <mat-icon>error_outline</mat-icon>
            <div>
              <strong>Antes de facturar falta:</strong>
              @for (m of s.missing; track m) { <span>{{ m }}</span> }
            </div>
          </div>
        } @else if (s.environment === '1') {
          <div class="notice">
            <mat-icon>science</mat-icon>
            <span>Ambiente de <b>pruebas</b> del SRI: estas facturas no tienen validez tributaria.</span>
          </div>
        }
      }

      <h3>Paciente</h3>
      @if (patientId()) {
        <div class="picked">
          <mat-icon>person</mat-icon>
          <strong>{{ patientName() || 'Paciente de esta ficha' }}</strong>
          @if (!data.patientId) {
            <button mat-button type="button" (click)="clearPatient()">Cambiar</button>
          }
        </div>
      } @else {
        <app-patient-picker (selected)="pickPatient($event)" hint="Para facturar cargos de su cuenta. Opcional." />
      }

      @if (charges().length) {
        <h3>Cargos de la cuenta sin facturar</h3>
        <div class="rows">
          @for (c of charges(); track c.id) {
            <div class="row" [class.off]="!c.selected">
              <mat-checkbox [(ngModel)]="c.selected" (change)="touch()">
                <span class="desc">{{ c.description }}</span>
                <span class="when">{{ c.issued_on | date: 'dd/MM/yyyy' }}</span>
              </mat-checkbox>
              <mat-form-field appearance="outline" subscriptSizing="dynamic" class="vat">
                <mat-select [(ngModel)]="c.vat_code" (selectionChange)="touch()" aria-label="IVA">
                  @for (v of catalogs()?.vat ?? []; track v.code) { <mat-option [value]="v.code">{{ v.label }}</mat-option> }
                </mat-select>
              </mat-form-field>
              <b class="numeric">$ {{ money(c.amount) }}</b>
            </div>
          }
        </div>
      } @else if (patientId() && !loadingCharges()) {
        <p class="muted">Este paciente no tiene cargos pendientes de facturar.</p>
      }

      <h3>Otros conceptos</h3>
      @for (m of manual(); track $index; let i = $index) {
        <div class="manual">
          <mat-form-field appearance="outline" subscriptSizing="dynamic" class="grow">
            <mat-label>Descripción</mat-label>
            <input matInput [(ngModel)]="m.description" (ngModelChange)="touch()" maxlength="300" />
          </mat-form-field>
          <mat-form-field appearance="outline" subscriptSizing="dynamic" class="qty">
            <mat-label>Cant.</mat-label>
            <input matInput type="number" min="1" [(ngModel)]="m.quantity" (ngModelChange)="touch()" />
          </mat-form-field>
          <mat-form-field appearance="outline" subscriptSizing="dynamic" class="price">
            <mat-label>Precio c/IVA</mat-label>
            <span matTextPrefix>$&nbsp;</span>
            <input matInput type="number" min="0" step="0.01" [(ngModel)]="m.price" (ngModelChange)="touch()" />
          </mat-form-field>
          <mat-form-field appearance="outline" subscriptSizing="dynamic" class="vat">
            <mat-select [(ngModel)]="m.vat_code" (selectionChange)="touch()" aria-label="IVA">
              @for (v of catalogs()?.vat ?? []; track v.code) { <mat-option [value]="v.code">{{ v.label }}</mat-option> }
            </mat-select>
          </mat-form-field>
          <button mat-icon-button type="button" (click)="removeManual(i)" aria-label="Quitar"><mat-icon>close</mat-icon></button>
        </div>
      }
      <button mat-stroked-button type="button" (click)="addManual()"><mat-icon>add</mat-icon>Agregar concepto</button>

      <h3>Comprador</h3>
      <div class="segmented">
        @if (patientId()) {
          <button type="button" [class.on]="buyerMode() === 'paciente'" (click)="buyerMode.set('paciente')">El paciente</button>
        }
        <button type="button" [class.on]="buyerMode() === 'otro'" (click)="buyerMode.set('otro')">Otra persona o empresa</button>
        <button type="button" [class.on]="buyerMode() === 'final'" (click)="buyerMode.set('final')">Consumidor final</button>
      </div>
      @if (buyerMode() === 'paciente') {
        <p class="muted">Con la cédula y el correo de su ficha. Si la ficha no tiene una cédula válida, se factura a consumidor final.</p>
      } @else if (buyerMode() === 'final') {
        <p class="muted">Solo hasta $ 50,00 por factura.</p>
      } @else {
        <div class="dialog-grid">
          <mat-form-field appearance="outline">
            <mat-label>Tipo</mat-label>
            <mat-select [(ngModel)]="buyer.id_type">
              @for (t of buyerTypes(); track t.code) { <mat-option [value]="t.code">{{ t.label }}</mat-option> }
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Número</mat-label>
            <input matInput [(ngModel)]="buyer.id_number" maxlength="20" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Nombre o razón social</mat-label>
            <input matInput [(ngModel)]="buyer.name" maxlength="300" />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Correo</mat-label>
            <input matInput type="email" [(ngModel)]="buyer.email" />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Teléfono</mat-label>
            <input matInput [(ngModel)]="buyer.phone" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Dirección</mat-label>
            <input matInput [(ngModel)]="buyer.address" maxlength="300" />
          </mat-form-field>
        </div>
      }

      <div class="dialog-grid">
        <mat-form-field appearance="outline">
          <mat-label>Forma de pago</mat-label>
          <mat-select [(ngModel)]="paymentMethod">
            @for (p of catalogs()?.payment_methods ?? []; track p.code) { <mat-option [value]="p.code">{{ p.label }}</mat-option> }
          </mat-select>
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Observación (opcional)</mat-label>
          <input matInput [(ngModel)]="notes" maxlength="300" />
        </mat-form-field>
      </div>

      <div class="totals">
        <span>Subtotal</span><b class="numeric">$ {{ money(totals().base) }}</b>
        <span>IVA</span><b class="numeric">$ {{ money(totals().vat) }}</b>
        <span class="big">Total</span><b class="numeric big">$ {{ money(totals().total) }}</b>
      </div>

      @if (error()) {
        <p class="error"><mat-icon>error_outline</mat-icon>{{ error() }}</p>
      }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>Cancelar</button>
      <button mat-flat-button (click)="save()" [disabled]="saving() || !totals().lines || !!settings()?.missing?.length">
        <mat-icon>receipt_long</mat-icon>{{ saving() ? 'Enviando al SRI…' : 'Emitir factura' }}
      </button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      h3 { margin: 18px 0 8px; font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--color-ink-faint); }
      .notice { display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px; border-radius: 12px; background: color-mix(in srgb, #c98a1e 12%, transparent); font-size: 0.86rem; }
      .notice.bad { background: color-mix(in srgb, var(--color-danger, #b3352b) 10%, transparent); }
      .notice div { display: grid; gap: 2px; }
      .picked { display: flex; align-items: center; gap: 8px; }
      .rows { display: grid; gap: 6px; }
      .row { display: grid; grid-template-columns: 1fr 150px auto; align-items: center; gap: 10px; }
      .row.off { opacity: 0.55; }
      .row .desc { font-weight: 600; margin-right: 8px; }
      .row .when { color: var(--color-ink-faint); font-size: 0.8rem; }
      .manual { display: grid; grid-template-columns: 1fr 80px 130px 150px auto; gap: 8px; align-items: center; margin-bottom: 8px; }
      .segmented { display: inline-flex; border: 1px solid var(--color-border); border-radius: 12px; overflow: hidden; margin-bottom: 8px; flex-wrap: wrap; }
      .segmented button { border: 0; background: transparent; padding: 8px 14px; font: inherit; cursor: pointer; color: inherit; }
      .segmented button.on { background: var(--color-primary); color: #fff; }
      .muted { color: var(--color-ink-faint); font-size: 0.86rem; margin: 4px 0; }
      .totals { display: grid; grid-template-columns: 1fr auto; gap: 4px 16px; margin: 14px 0 0 auto; max-width: 280px; }
      .totals .big { font-size: 1.15rem; font-weight: 800; }
      .error { display: flex; gap: 8px; align-items: center; color: var(--color-danger, #b3352b); }
      @media (max-width: 640px) {
        .manual { grid-template-columns: 1fr 1fr; }
        .row { grid-template-columns: 1fr auto; }
        .row .vat { grid-column: 1 / -1; }
      }
    `,
  ],
})
export class InvoiceCreateDialogComponent implements OnInit {
  readonly data = inject<InvoiceCreateData>(MAT_DIALOG_DATA);
  private readonly ref = inject(MatDialogRef<InvoiceCreateDialogComponent, Invoice>);
  private readonly service = inject(InvoicingService);

  readonly money = formatMoney;
  readonly settings = signal<InvoicingSettings | null>(null);
  readonly catalogs = signal<InvoicingCatalogs | null>(null);
  readonly patientId = signal<string | null>(this.data.patientId ?? null);
  readonly patientName = signal<string | null>(this.data.patientName ?? null);
  readonly charges = signal<ChargeRow[]>([]);
  readonly loadingCharges = signal(false);
  readonly manual = signal<ManualRow[]>([]);
  readonly buyerMode = signal<BuyerMode>(this.data.patientId ? 'paciente' : 'final');
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  private readonly version = signal(0);

  buyer = { id_type: '05', id_number: '', name: '', email: '', phone: '', address: '' };
  paymentMethod = '01';
  notes = '';

  readonly buyerTypes = computed(() => (this.catalogs()?.id_types ?? []).filter((t) => t.code !== '07'));

  readonly totals = computed(() => {
    this.version();
    const rate = (code: string) => +(this.catalogs()?.vat.find((v) => v.code === code)?.rate ?? 0);
    let base = 0;
    let vat = 0;
    let lines = 0;
    for (const c of this.charges()) {
      if (!c.selected) continue;
      const s = split(+c.amount, rate(c.vat_code));
      base += s.base;
      vat += s.vat;
      lines++;
    }
    for (const m of this.manual()) {
      if (!m.description.trim() || !(m.price > 0) || !(m.quantity > 0)) continue;
      const s = split(m.price * m.quantity, rate(m.vat_code));
      base += s.base;
      vat += s.vat;
      lines++;
    }
    return { base, vat, total: base + vat, lines };
  });

  async ngOnInit(): Promise<void> {
    const [settings, catalogs] = await Promise.all([
      firstValueFrom(this.service.settings()),
      firstValueFrom(this.service.catalogs()),
    ]);
    this.settings.set(settings);
    this.catalogs.set(catalogs);
    if (this.patientId()) await this.loadCharges();
    else this.addManual();
  }

  touch(): void {
    this.version.update((v) => v + 1);
  }

  async pickPatient(p: PatientListItem): Promise<void> {
    this.patientId.set(p.id);
    this.patientName.set(`${p.first_name} ${p.last_name}`);
    this.buyerMode.set('paciente');
    await this.loadCharges();
  }

  clearPatient(): void {
    this.patientId.set(null);
    this.patientName.set(null);
    this.charges.set([]);
    if (this.buyerMode() === 'paciente') this.buyerMode.set('final');
  }

  private async loadCharges(): Promise<void> {
    const id = this.patientId();
    if (!id) return;
    this.loadingCharges.set(true);
    try {
      const list = await firstValueFrom(this.service.invoiceableCharges(id));
      this.charges.set(list.map((c) => ({ ...c, selected: true, vat_code: '0' })));
      if (!list.length && !this.manual().length) this.addManual();
    } finally {
      this.loadingCharges.set(false);
      this.touch();
    }
  }

  addManual(): void {
    this.manual.update((m) => [...m, { description: '', quantity: 1, price: 0, vat_code: '0' }]);
  }

  removeManual(i: number): void {
    this.manual.update((m) => m.filter((_, j) => j !== i));
  }

  async save(): Promise<void> {
    this.error.set(null);
    const body: InvoiceCreate = {
      patient_id: this.patientId(),
      payment_method: this.paymentMethod,
      notes: this.notes.trim() || null,
      items: [
        ...this.charges().filter((c) => c.selected).map((c) => ({ charge_id: c.id, vat_code: c.vat_code })),
        ...this.manual()
          .filter((m) => m.description.trim() && m.price > 0)
          .map((m) => ({
            description: m.description.trim(),
            quantity: String(m.quantity || 1),
            unit_price: String(m.price),
            price_includes_vat: true,
            vat_code: m.vat_code,
          })),
      ],
      buyer:
        this.buyerMode() === 'final'
          ? { id_type: '07', id_number: '9999999999999', name: 'CONSUMIDOR FINAL' }
          : this.buyerMode() === 'otro'
            ? {
                id_type: this.buyer.id_type,
                id_number: this.buyer.id_number.trim(),
                name: this.buyer.name.trim(),
                email: this.buyer.email.trim() || null,
                phone: this.buyer.phone.trim() || null,
                address: this.buyer.address.trim() || null,
              }
            : null,
    };
    if (!body.items.length) {
      this.error.set('Agregue al menos un concepto con precio.');
      return;
    }
    this.saving.set(true);
    try {
      this.ref.close(await firstValueFrom(this.service.create(body)));
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.error.set(
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail) && detail[0]?.msg
            ? String(detail[0].msg).replace('Value error, ', '')
            : 'No se pudo emitir la factura.',
      );
    } finally {
      this.saving.set(false);
    }
  }
}

export function openInvoiceCreate(dialog: MatDialog, data: InvoiceCreateData = {}): Promise<Invoice | undefined> {
  return firstValueFrom(
    dialog
      .open<InvoiceCreateDialogComponent, InvoiceCreateData, Invoice>(InvoiceCreateDialogComponent, {
        data,
        width: '760px',
        maxWidth: '96vw',
        panelClass: 'app-dialog',
      })
      .afterClosed(),
  );
}
