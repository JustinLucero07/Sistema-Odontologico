import { DatePipe } from '@angular/common';
import { Component, Input, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import {
  AccountStatement,
  CHARGE_STATUS_LABELS,
  Charge,
  INSTALLMENT_LABELS,
  Payment,
  PaymentMethodOption,
  formatMoney,
} from '../../core/models/finance.models';
import { FinanceService } from '../../core/services/finance.service';

type Pending = { kind: 'payment'; item: Payment } | { kind: 'charge'; item: Charge };

@Component({
  selector: 'app-account-tab',
  standalone: true,
  imports: [
    DatePipe,
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatTooltipModule,
  ],
  templateUrl: './account-tab.component.html',
  styleUrl: './account-tab.component.scss',
})
export class AccountTabComponent implements OnInit {
  @Input({ required: true }) patientId!: string;

  private readonly finance = inject(FinanceService);
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);
  readonly auth = inject(AuthService);

  readonly account = signal<AccountStatement | null>(null);
  readonly methods = signal<PaymentMethodOption[]>([]);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly showChargeForm = signal(false);
  readonly showPaymentForm = signal(false);
  readonly planningFor = signal<Charge | null>(null);
  readonly voiding = signal<Pending | null>(null);
  voidReason = '';

  readonly chargeLabels = CHARGE_STATUS_LABELS;
  readonly installmentLabels = INSTALLMENT_LABELS;
  readonly money = formatMoney;

  readonly chargeForm = this.fb.nonNullable.group({
    description: ['', Validators.required],
    amount: ['', [Validators.required, Validators.pattern(/^\d+([.,]\d{1,2})?$/)]],
    notes: [''],
  });

  readonly paymentForm = this.fb.nonNullable.group({
    amount: ['', [Validators.required, Validators.pattern(/^\d+([.,]\d{1,2})?$/)]],
    method: ['efectivo', Validators.required],
    charge_id: [''],
    reference: [''],
    notes: [''],
  });

  readonly planForm = this.fb.nonNullable.group({
    count: [3, [Validators.required, Validators.min(2), Validators.max(36)]],
    first_due_on: ['', Validators.required],
    every_days: [30, [Validators.required, Validators.min(7), Validators.max(90)]],
  });

  get canWrite(): boolean {
    return this.auth.hasPermission('payments:write');
  }

  /** Charges that can still take money — what the payment form offers. */
  readonly openCharges = computed(
    () => this.account()?.charges.filter((c) => c.status === 'pendiente' || c.status === 'parcial') ?? [],
  );

  readonly selectedMethodNeedsReference = computed(() => {
    const code = this.paymentForm.controls.method.value;
    return this.methods().find((m) => m.code === code)?.requires_reference ?? false;
  });

  /** A negative balance means the clinic is holding the patient's money. */
  readonly balanceTone = computed(() => {
    const balance = Number(this.account()?.balance ?? 0);
    if (balance > 0) return 'owed';
    if (balance < 0) return 'credit';
    return 'settled';
  });

  async ngOnInit(): Promise<void> {
    this.methods.set(await firstValueFrom(this.finance.getMethods()));
    await this.reload();
  }

  private async reload(): Promise<void> {
    this.loading.set(true);
    try {
      this.account.set(await firstValueFrom(this.finance.getAccount(this.patientId)));
    } finally {
      this.loading.set(false);
    }
  }

  /** The form accepts a comma as the decimal mark, which is what a Spanish
   *  keyboard produces; the API only speaks dots. */
  private normalize(raw: string): string {
    return raw.replace(',', '.');
  }

  async submitCharge(): Promise<void> {
    if (this.chargeForm.invalid || this.saving()) return;
    this.saving.set(true);
    try {
      const raw = this.chargeForm.getRawValue();
      await firstValueFrom(
        this.finance.createCharge(this.patientId, {
          description: raw.description,
          amount: this.normalize(raw.amount),
          notes: raw.notes || null,
        }),
      );
      this.chargeForm.reset();
      this.showChargeForm.set(false);
      await this.reload();
      this.snackBar.open('Cargo registrado', 'Cerrar', { duration: 3000 });
    } catch (error) {
      this.report(error, 'No se pudo registrar el cargo');
    } finally {
      this.saving.set(false);
    }
  }

  async submitPayment(): Promise<void> {
    if (this.paymentForm.invalid || this.saving()) return;
    this.saving.set(true);
    try {
      const raw = this.paymentForm.getRawValue();
      await firstValueFrom(
        this.finance.createPayment(this.patientId, {
          amount: this.normalize(raw.amount),
          method: raw.method,
          charge_id: raw.charge_id || null,
          reference: raw.reference || null,
          notes: raw.notes || null,
        }),
      );
      this.paymentForm.reset({ method: 'efectivo' });
      this.showPaymentForm.set(false);
      await this.reload();
      this.snackBar.open('Pago registrado', 'Cerrar', { duration: 3000 });
    } catch (error) {
      this.report(error, 'No se pudo registrar el pago');
    } finally {
      this.saving.set(false);
    }
  }

  openPlan(charge: Charge): void {
    this.planningFor.set(charge);
    this.planForm.reset({ count: 3, every_days: 30, first_due_on: '' });
  }

  async submitPlan(): Promise<void> {
    const charge = this.planningFor();
    if (!charge || this.planForm.invalid) return;
    this.saving.set(true);
    try {
      const raw = this.planForm.getRawValue();
      await firstValueFrom(
        this.finance.setInstallments(charge.id, {
          count: raw.count,
          first_due_on: raw.first_due_on,
          every_days: raw.every_days,
        }),
      );
      this.planningFor.set(null);
      await this.reload();
      this.snackBar.open('Plan de cuotas guardado', 'Cerrar', { duration: 3000 });
    } catch (error) {
      this.report(error, 'No se pudo guardar el plan de cuotas');
    } finally {
      this.saving.set(false);
    }
  }

  askVoid(pending: Pending): void {
    this.voiding.set(pending);
    this.voidReason = '';
  }

  async confirmVoid(): Promise<void> {
    const pending = this.voiding();
    if (!pending || this.voidReason.trim().length < 3) return;
    this.saving.set(true);
    try {
      const call =
        pending.kind === 'payment'
          ? this.finance.voidPayment(pending.item.id, this.voidReason.trim())
          : this.finance.voidCharge(pending.item.id, this.voidReason.trim());
      await firstValueFrom(call);
      this.voiding.set(null);
      await this.reload();
      this.snackBar.open('Anulado y registrado en la auditoría', 'Cerrar', { duration: 3500 });
    } catch (error) {
      this.report(error, 'No se pudo anular');
    } finally {
      this.saving.set(false);
    }
  }

  methodLabel(code: string): string {
    return this.methods().find((m) => m.code === code)?.label ?? code;
  }

  chargeLabel(chargeId: string | null): string {
    if (!chargeId) return 'A cuenta';
    return this.account()?.charges.find((c) => c.id === chargeId)?.description ?? '—';
  }

  /** The API's messages are specific (which cap was exceeded, by how much);
   *  showing ours instead would throw away the useful part. */
  private report(error: unknown, fallback: string): void {
    const detail = (error as { error?: { detail?: unknown } })?.error?.detail;
    const message = typeof detail === 'string' ? detail : fallback;
    this.snackBar.open(message, 'Cerrar', { duration: 7000 });
  }
}
