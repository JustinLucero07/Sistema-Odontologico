import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatMenuModule } from '@angular/material/menu';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import {
  CREDIT_STATUS_LABELS,
  CreditDetail,
  CreditFrequency,
  CreditOptions,
  CreditPaymentRow,
  INSTALLMENT_STATUS_LABELS,
} from '../../core/models/credit.models';
import { PaymentMethodOption, formatMoney } from '../../core/models/finance.models';
import { CreditsService } from '../../core/services/credits.service';
import { FinanceService } from '../../core/services/finance.service';
import { LegalService } from '../../core/services/legal.service';
import { PatientsService } from '../../core/services/patients.service';
import { promptVoidReason } from '../confirm-dialog/prompt-dialog.component';
import { printCreditAgreement } from '../print/credit-print';
import { printReceipt } from '../print/receipt-print';

type Panel = 'pay' | 'edit' | 'restructure' | null;

function isoIn(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

@Component({
  selector: 'app-credit-detail-dialog',
  standalone: true,
  imports: [
    DatePipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatSelectModule,
    MatTooltipModule,
  ],
  templateUrl: './credit-detail-dialog.component.html',
  styleUrl: './credit-detail-dialog.component.scss',
})
export class CreditDetailDialogComponent implements OnInit {
  private readonly data = inject<{ creditId: string }>(MAT_DIALOG_DATA);
  private readonly ref = inject(MatDialogRef<CreditDetailDialogComponent, boolean>);
  private readonly credits = inject(CreditsService);
  private readonly finance = inject(FinanceService);
  private readonly legal = inject(LegalService);
  private readonly patients = inject(PatientsService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);
  readonly auth = inject(AuthService);

  readonly money = formatMoney;
  readonly statusLabels = CREDIT_STATUS_LABELS;
  readonly rowLabels = INSTALLMENT_STATUS_LABELS;
  readonly canWrite = this.auth.hasPermission('payments:write');

  readonly credit = signal<CreditDetail | null>(null);
  readonly options = signal<CreditOptions | null>(null);
  readonly methods = signal<PaymentMethodOption[]>([]);
  readonly panel = signal<Panel>(null);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  private changed = false;

  readonly payForm = this.fb.nonNullable.group({
    amount: ['', [Validators.required, Validators.pattern(/^\d+([.,]\d{1,2})?$/)]],
    method: ['efectivo'],
    reference: [''],
  });

  readonly editForm = this.fb.nonNullable.group({
    guarantor_name: [''],
    guarantor_id_number: [''],
    guarantor_phone: [''],
    notes: [''],
  });

  readonly restructureForm = this.fb.nonNullable.group({
    installment_count: [3, [Validators.required, Validators.min(1)]],
    frequency: ['mensual' as CreditFrequency],
    first_due_on: [isoIn(30), Validators.required],
  });

  async ngOnInit(): Promise<void> {
    const [credit, options, methods] = await Promise.all([
      firstValueFrom(this.credits.get(this.data.creditId)),
      firstValueFrom(this.credits.getOptions()),
      firstValueFrom(this.finance.getMethods()),
    ]);
    this.credit.set(credit);
    this.options.set(options);
    this.methods.set(methods);
  }

  progress(c: CreditDetail): number {
    return +c.total > 0 ? Math.min(100, (+c.paid / +c.total) * 100) : 0;
  }

  needsReference(): boolean {
    return this.methods().find((m) => m.code === this.payForm.controls.method.value)?.requires_reference ?? false;
  }

  open(panel: Panel): void {
    const c = this.credit();
    if (!c) return;
    this.error.set(null);
    if (panel === 'pay') {
      this.payForm.reset({ amount: c.next_amount ?? '', method: 'efectivo', reference: '' });
    }
    if (panel === 'edit') {
      this.editForm.reset({
        guarantor_name: c.guarantor_name ?? '',
        guarantor_id_number: c.guarantor_id_number ?? '',
        guarantor_phone: c.guarantor_phone ?? '',
        notes: c.notes ?? '',
      });
    }
    if (panel === 'restructure') {
      this.restructureForm.reset({ installment_count: 3, frequency: c.frequency, first_due_on: isoIn(30) });
    }
    this.panel.set(this.panel() === panel ? null : panel);
  }

  private fail(err: unknown, fallback: string): void {
    const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
    this.error.set(
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail) && typeof detail[0]?.msg === 'string'
          ? detail[0].msg.replace('Value error, ', '')
          : fallback,
    );
  }

  private done(updated: CreditDetail, message: string): void {
    this.credit.set(updated);
    this.panel.set(null);
    this.changed = true;
    this.snackBar.open(message, 'Cerrar', { duration: 3000 });
  }

  async pay(): Promise<void> {
    const c = this.credit();
    if (!c || this.payForm.invalid) {
      this.payForm.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    const v = this.payForm.getRawValue();
    try {
      const updated = await firstValueFrom(
        this.credits.pay(c.id, {
          amount: v.amount.replace(',', '.'),
          method: v.method,
          reference: v.reference.trim() || null,
        }),
      );
      this.done(updated, 'Pago de cuota registrado');
      // El recibo sale solo: es lo que el paciente se lleva.
      const newest = updated.payments.find((p) => !p.voided_at);
      if (newest) await this.receipt(newest);
    } catch (err) {
      this.fail(err, 'No se pudo registrar el pago');
    } finally {
      this.saving.set(false);
    }
  }

  async saveEdit(): Promise<void> {
    const c = this.credit();
    if (!c) return;
    this.saving.set(true);
    const v = this.editForm.getRawValue();
    try {
      const updated = await firstValueFrom(
        this.credits.update(c.id, {
          guarantor_name: v.guarantor_name.trim() || null,
          guarantor_id_number: v.guarantor_id_number.trim() || null,
          guarantor_phone: v.guarantor_phone.trim() || null,
          notes: v.notes.trim() || null,
        }),
      );
      this.done(updated, 'Crédito actualizado');
    } catch (err) {
      this.fail(err, 'No se pudo guardar');
    } finally {
      this.saving.set(false);
    }
  }

  async restructure(): Promise<void> {
    const c = this.credit();
    if (!c || this.restructureForm.invalid) return;
    this.saving.set(true);
    const v = this.restructureForm.getRawValue();
    try {
      const updated = await firstValueFrom(
        this.credits.restructure(c.id, {
          installment_count: Number(v.installment_count),
          frequency: v.frequency,
          first_due_on: v.first_due_on,
        }),
      );
      this.done(updated, 'Saldo refinanciado');
    } catch (err) {
      this.fail(err, 'No se pudo refinanciar');
    } finally {
      this.saving.set(false);
    }
  }

  async voidCredit(): Promise<void> {
    const c = this.credit();
    if (!c) return;
    const reason = await promptVoidReason(this.dialog, 'crédito');
    if (!reason) return;
    try {
      this.done(await firstValueFrom(this.credits.void(c.id, reason)), 'Crédito anulado');
    } catch (err) {
      this.fail(err, 'No se pudo anular el crédito');
    }
  }

  async voidPayment(row: CreditPaymentRow): Promise<void> {
    const c = this.credit();
    if (!c) return;
    const reason = await promptVoidReason(this.dialog, 'pago de cuota');
    if (!reason) return;
    await firstValueFrom(this.finance.voidPayment(row.payment_ids[0], reason));
    this.done(await firstValueFrom(this.credits.get(c.id)), 'Pago anulado');
  }

  async printAgreement(): Promise<void> {
    const c = this.credit();
    if (!c) return;
    const [clinic, patient] = await Promise.all([
      firstValueFrom(this.legal.getController()),
      firstValueFrom(this.patients.getPatient(c.patient_id)),
    ]);
    if (!printCreditAgreement(c, clinic, { national_id: patient.national_id })) {
      this.snackBar.open('El navegador bloqueó la ventana de impresión', 'Cerrar', { duration: 4000 });
    }
  }

  async receipt(row: CreditPaymentRow): Promise<void> {
    const c = this.credit();
    if (!c) return;
    const [clinic, patient] = await Promise.all([
      firstValueFrom(this.legal.getController()),
      firstValueFrom(this.patients.getPatient(c.patient_id)),
    ]);
    printReceipt(
      {
        number: row.group_id.slice(0, 8).toUpperCase(),
        received_on: row.received_on,
        patient_name: c.patient_name,
        patient_id_number: patient.national_id,
        concept: `Cuota de crédito · ${c.charge_description}`,
        amount: row.amount,
        method_label: row.method_label,
        reference: row.reference,
        received_by: this.auth.currentUser() ? `${this.auth.currentUser()!.first_name} ${this.auth.currentUser()!.last_name}` : null,
        balance_after: c.pending,
      },
      clinic,
    );
  }

  /** Recordatorio por WhatsApp, redactado con la cuota que toca. Solo si el
   *  paciente no retiró su autorización de mensajes. */
  whatsappLink(c: CreditDetail): string | null {
    if (!c.patient_phone || !c.communications_allowed || !c.next_amount || !c.next_due_on) return null;
    const first = c.patient_name.split(' ')[0];
    const due = new Date(`${c.next_due_on}T00:00:00`).toLocaleDateString('es', { day: 'numeric', month: 'long' });
    const text =
      c.status === 'vencido'
        ? `Hola ${first}, le recordamos que tiene una cuota pendiente de $${this.money(c.next_amount)} que venció el ${due}. Si ya la pagó, por favor ignore este mensaje.`
        : `Hola ${first}, le recordamos que su próxima cuota de $${this.money(c.next_amount)} vence el ${due}. ¡Gracias!`;
    return `https://wa.me/${c.patient_phone.replace(/[^\d]/g, '')}?text=${encodeURIComponent(text)}`;
  }

  goToPatient(c: CreditDetail): void {
    this.ref.close(this.changed);
    this.router.navigate(['/patients', c.patient_id]);
  }
}

export function openCreditDetail(dialog: MatDialog, creditId: string): Promise<boolean | undefined> {
  return firstValueFrom(
    dialog
      .open(CreditDetailDialogComponent, {
        data: { creditId },
        width: '860px',
        maxWidth: '96vw',
        panelClass: 'app-dialog',
        autoFocus: false,
      })
      .afterClosed(),
  );
}
