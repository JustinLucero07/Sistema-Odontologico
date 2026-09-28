import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { debounceTime, firstValueFrom } from 'rxjs';

import { CreditDetail, CreditFrequency, CreditOptions, CreditPreview } from '../../core/models/credit.models';
import { PaymentMethodOption, formatMoney } from '../../core/models/finance.models';
import { CreditsService } from '../../core/services/credits.service';
import { FinanceService } from '../../core/services/finance.service';

export interface CreditCreateData {
  patientId: string;
  charge: { id: string; description: string; pending: string };
}

function isoIn(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

@Component({
  selector: 'app-credit-create-dialog',
  standalone: true,
  imports: [
    DatePipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
  ],
  template: `
    <h2 mat-dialog-title>Financiar en cuotas</h2>
    <form [formGroup]="form" (ngSubmit)="save()">
      <mat-dialog-content>
        <div class="charge">
          <mat-icon>receipt_long</mat-icon>
          <div>
            <strong>{{ data.charge.description }}</strong>
            <span>Saldo a financiar: $ {{ money(data.charge.pending) }}</span>
          </div>
        </div>

        <h3>Condiciones</h3>
        <div class="dialog-grid">
          <mat-form-field appearance="outline">
            <mat-label>Entrada (opcional)</mat-label>
            <span matTextPrefix>$&nbsp;</span>
            <input matInput formControlName="down_payment" inputmode="decimal" />
            <mat-hint>Se cobra ahora y se descuenta del saldo</mat-hint>
          </mat-form-field>
          @if (hasDownPayment()) {
            <mat-form-field appearance="outline">
              <mat-label>Medio de la entrada</mat-label>
              <mat-select formControlName="down_payment_method">
                @for (m of methods(); track m.code) {
                  <mat-option [value]="m.code">{{ m.label }}</mat-option>
                }
              </mat-select>
            </mat-form-field>
            @if (needsReference()) {
              <mat-form-field appearance="outline" class="full">
                <mat-label>Referencia de la entrada</mat-label>
                <input matInput formControlName="down_payment_reference" />
              </mat-form-field>
            }
          }
          <mat-form-field appearance="outline">
            <mat-label>Número de cuotas</mat-label>
            <input matInput type="number" formControlName="installment_count" min="1" [max]="options()?.max_installments ?? 48" />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Frecuencia</mat-label>
            <mat-select formControlName="frequency">
              @for (f of options()?.frequencies ?? []; track f.code) {
                <mat-option [value]="f.code">{{ f.label }}</mat-option>
              }
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Primera cuota</mat-label>
            <input matInput type="date" formControlName="first_due_on" />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Interés mensual</mat-label>
            <input matInput formControlName="monthly_rate" inputmode="decimal" />
            <span matTextSuffix>%</span>
            <mat-hint>0 = sin interés</mat-hint>
          </mat-form-field>
        </div>

        @if (preview(); as p) {
          <div class="summary">
            <div><span>Cuota</span><b>$ {{ money(p.installment_amount) }}</b></div>
            <div><span>Total en cuotas</span><b>$ {{ money(p.total) }}</b></div>
            <div><span>Costo del financiamiento</span><b>$ {{ money(p.total_interest) }}</b></div>
            <div><span>Tasa anual</span><b>{{ p.annual_rate }} %</b></div>
          </div>
          @if (+p.total_interest > 0) {
            <p class="legal">
              <mat-icon>gavel</mat-icon>
              La tasa no puede superar la máxima vigente fijada por el Banco Central del Ecuador para créditos de
              consumo. El paciente debe conocer el costo total del financiamiento antes de firmar.
            </p>
          }
          <div class="schedule">
            <table>
              <thead><tr><th>N.°</th><th>Vence</th><th class="num">Capital</th><th class="num">Interés</th><th class="num">Cuota</th></tr></thead>
              <tbody>
                @for (r of p.rows; track r.number) {
                  <tr>
                    <td>{{ r.number }}</td>
                    <td>{{ r.due_on | date: 'dd/MM/yyyy' }}</td>
                    <td class="num">{{ money(r.principal) }}</td>
                    <td class="num">{{ money(r.interest) }}</td>
                    <td class="num"><b>{{ money(r.amount) }}</b></td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }

        <h3>Garante (opcional)</h3>
        <div class="dialog-grid">
          <mat-form-field appearance="outline" class="full">
            <mat-label>Nombre del garante</mat-label>
            <input matInput formControlName="guarantor_name" />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Cédula</mat-label>
            <input matInput formControlName="guarantor_id_number" />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Teléfono</mat-label>
            <input matInput formControlName="guarantor_phone" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Notas</mat-label>
            <textarea matInput formControlName="notes" rows="2"></textarea>
          </mat-form-field>
        </div>

        @if (error()) {
          <p class="dialog-error">{{ error() }}</p>
        }
      </mat-dialog-content>
      <mat-dialog-actions align="end">
        <button mat-button type="button" mat-dialog-close>Cancelar</button>
        <button mat-flat-button type="submit" [disabled]="saving() || !preview()">
          {{ saving() ? 'Creando…' : 'Crear crédito' }}
        </button>
      </mat-dialog-actions>
    </form>
  `,
  styles: [
    `
      h3 { margin: 14px 0 6px; font-size: 0.74rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--color-ink-faint); }
      .charge { display: flex; gap: 12px; align-items: center; padding: 12px 14px; border-radius: var(--radius-sm); background: var(--color-primary-soft); }
      .charge mat-icon { color: var(--color-primary); }
      .charge div { display: grid; }
      .charge span { font-size: 0.82rem; color: var(--color-ink-soft); }
      .summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 8px 0; padding: 12px 14px; border-radius: var(--radius-md); background: var(--glass-field-bg); border: 1px solid var(--color-border); }
      .summary div { display: grid; }
      .summary span { font-size: 0.72rem; color: var(--color-ink-faint); }
      .summary b { font-size: 1.05rem; }
      .summary div:first-child b { color: var(--color-primary); font-size: 1.25rem; }
      .legal { display: flex; gap: 8px; margin: 6px 0; padding: 8px 12px; border-radius: var(--radius-sm); background: var(--color-accent-soft); font-size: 0.78rem; line-height: 1.45; }
      .legal mat-icon { color: var(--color-accent); flex-shrink: 0; font-size: 18px; width: 18px; height: 18px; }
      .schedule { max-height: 220px; overflow-y: auto; border: 1px solid var(--color-border); border-radius: var(--radius-sm); }
      table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
      th { position: sticky; top: 0; background: var(--color-surface); text-align: left; font-size: 0.72rem; color: var(--color-ink-faint); padding: 6px 10px; }
      td { padding: 5px 10px; border-top: 1px solid var(--color-border); }
      .num { text-align: right; font-variant-numeric: tabular-nums; }
      @media (max-width: 560px) { .summary { grid-template-columns: repeat(2, 1fr); } }
    `,
  ],
})
export class CreditCreateDialogComponent implements OnInit {
  readonly data = inject<CreditCreateData>(MAT_DIALOG_DATA);
  private readonly ref = inject(MatDialogRef<CreditCreateDialogComponent, CreditDetail>);
  private readonly credits = inject(CreditsService);
  private readonly finance = inject(FinanceService);
  private readonly destroyRef = inject(DestroyRef);

  readonly money = formatMoney;
  readonly options = signal<CreditOptions | null>(null);
  readonly methods = signal<PaymentMethodOption[]>([]);
  readonly preview = signal<CreditPreview | null>(null);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);

  readonly form = inject(FormBuilder).nonNullable.group({
    down_payment: ['0'],
    down_payment_method: ['efectivo'],
    down_payment_reference: [''],
    installment_count: [6, [Validators.required, Validators.min(1)]],
    frequency: ['mensual' as CreditFrequency],
    first_due_on: [isoIn(30), Validators.required],
    monthly_rate: ['0'],
    guarantor_name: [''],
    guarantor_id_number: [''],
    guarantor_phone: [''],
    notes: [''],
  });

  hasDownPayment(): boolean {
    return this.num(this.form.controls.down_payment.value) > 0;
  }

  needsReference(): boolean {
    return this.methods().find((m) => m.code === this.form.controls.down_payment_method.value)?.requires_reference ?? false;
  }

  private num(v: string | number): number {
    return Number(String(v ?? '0').replace(',', '.')) || 0;
  }

  async ngOnInit(): Promise<void> {
    const [options, methods] = await Promise.all([
      firstValueFrom(this.credits.getOptions()),
      firstValueFrom(this.finance.getMethods()),
    ]);
    this.options.set(options);
    this.methods.set(methods);
    this.form.valueChanges
      .pipe(debounceTime(250), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => void this.refreshPreview());
    await this.refreshPreview();
  }

  private async refreshPreview(): Promise<void> {
    const v = this.form.getRawValue();
    const principal = this.num(this.data.charge.pending) - this.num(v.down_payment);
    const count = Number(v.installment_count);
    if (principal <= 0 || !count || count < 1 || !v.first_due_on) {
      this.preview.set(null);
      return;
    }
    try {
      this.preview.set(
        await firstValueFrom(
          this.credits.preview({
            principal: principal.toFixed(2),
            installment_count: count,
            monthly_rate: String(this.num(v.monthly_rate)),
            frequency: v.frequency,
            first_due_on: v.first_due_on,
          }),
        ),
      );
      this.error.set(null);
    } catch {
      this.preview.set(null);
    }
  }

  async save(): Promise<void> {
    if (this.form.invalid || !this.preview()) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    const v = this.form.getRawValue();
    try {
      const created = await firstValueFrom(
        this.credits.create(this.data.patientId, {
          charge_id: this.data.charge.id,
          installment_count: Number(v.installment_count),
          frequency: v.frequency,
          first_due_on: v.first_due_on,
          monthly_rate: String(this.num(v.monthly_rate)),
          down_payment: this.num(v.down_payment).toFixed(2),
          down_payment_method: v.down_payment_method,
          down_payment_reference: v.down_payment_reference.trim() || null,
          guarantor_name: v.guarantor_name.trim() || null,
          guarantor_id_number: v.guarantor_id_number.trim() || null,
          guarantor_phone: v.guarantor_phone.trim() || null,
          notes: v.notes.trim() || null,
        }),
      );
      this.ref.close(created);
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.error.set(
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail) && typeof detail[0]?.msg === 'string'
            ? detail[0].msg
            : 'No se pudo crear el crédito.',
      );
    } finally {
      this.saving.set(false);
    }
  }
}

export function openCreditCreate(dialog: MatDialog, data: CreditCreateData): Promise<CreditDetail | undefined> {
  return firstValueFrom(
    dialog
      .open(CreditCreateDialogComponent, { data, width: '760px', maxWidth: '96vw', panelClass: 'app-dialog', autoFocus: false })
      .afterClosed(),
  );
}
