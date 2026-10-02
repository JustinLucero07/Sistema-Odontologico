import { DatePipe } from '@angular/common';
import { Component, OnInit, TemplateRef, ViewChild, computed, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { CREDIT_STATUS_LABELS, Credit, CreditStatus, CreditSummary } from '../../core/models/credit.models';
import { Charge, formatMoney } from '../../core/models/finance.models';
import { PatientListItem } from '../../core/models/patient.models';
import { CreditsService } from '../../core/services/credits.service';
import { FinanceService } from '../../core/services/finance.service';
import { openCreditCreate } from '../../shared/credits/credit-create-dialog.component';
import { openCreditDetail } from '../../shared/credits/credit-detail-dialog.component';
import { PatientPickerComponent } from '../../shared/patient-picker/patient-picker.component';

type Filter = 'todos' | CreditStatus;

@Component({
  selector: 'app-credits-page',
  standalone: true,
  imports: [
    DatePipe,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    PatientPickerComponent,
  ],
  templateUrl: './credits-page.component.html',
  styleUrl: './credits-page.component.scss',
})
export class CreditsPageComponent implements OnInit {
  private readonly creditsService = inject(CreditsService);
  private readonly finance = inject(FinanceService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly route = inject(ActivatedRoute);
  readonly auth = inject(AuthService);

  @ViewChild('newDialog') newDialog!: TemplateRef<unknown>;
  private newRef: MatDialogRef<unknown> | null = null;

  readonly money = formatMoney;
  readonly labels = CREDIT_STATUS_LABELS;
  readonly canWrite = this.auth.hasPermission('payments:write');

  readonly credits = signal<Credit[]>([]);
  readonly summary = signal<CreditSummary | null>(null);
  readonly filter = signal<Filter>('todos');
  readonly search = signal('');
  readonly loading = signal(true);

  // Alta desde esta pantalla: primero el paciente, luego el cargo a financiar.
  readonly pickedPatient = signal<PatientListItem | null>(null);
  readonly openCharges = signal<Charge[]>([]);

  readonly filters: { code: Filter; label: string }[] = [
    { code: 'todos', label: 'Todos' },
    { code: 'vencido', label: 'Con atraso' },
    { code: 'al_dia', label: 'Al día' },
    { code: 'pagado', label: 'Pagados' },
    { code: 'anulado', label: 'Anulados' },
  ];

  readonly visible = computed(() => {
    const term = this.search().trim().toLowerCase();
    return this.credits().filter(
      (c) =>
        (this.filter() === 'todos' || c.status === this.filter()) &&
        (!term || c.patient_name.toLowerCase().includes(term) || c.charge_description.toLowerCase().includes(term)),
    );
  });

  count(code: Filter): number {
    return code === 'todos' ? this.credits().length : this.credits().filter((c) => c.status === code).length;
  }

  progress(c: Credit): number {
    return +c.total > 0 ? Math.min(100, (+c.paid / +c.total) * 100) : 0;
  }

  async ngOnInit(): Promise<void> {
    const f = this.route.snapshot.queryParamMap.get('estado') as Filter | null;
    if (f && this.filters.some((x) => x.code === f)) this.filter.set(f);
    await this.reload();
  }

  async reload(): Promise<void> {
    try {
      const [credits, summary] = await Promise.all([
        firstValueFrom(this.creditsService.list()),
        firstValueFrom(this.creditsService.summary()),
      ]);
      this.credits.set(credits);
      this.summary.set(summary);
    } finally {
      this.loading.set(false);
    }
  }

  async openDetail(c: Credit): Promise<void> {
    await openCreditDetail(this.dialog, c.id);
    await this.reload();
  }

  startNew(): void {
    this.pickedPatient.set(null);
    this.openCharges.set([]);
    this.newRef = this.dialog.open(this.newDialog, { width: '560px', maxWidth: '96vw', panelClass: 'app-dialog' });
  }

  async pickPatient(patient: PatientListItem): Promise<void> {
    this.pickedPatient.set(patient);
    const account = await firstValueFrom(this.finance.getAccount(patient.id));
    const financed = new Set(
      this.credits()
        .filter((c) => c.status !== 'anulado')
        .flatMap((c) => [c.charge_id, c.interest_charge_id]),
    );
    this.openCharges.set(
      account.charges.filter((ch) => +ch.pending > 0 && ch.status !== 'anulada' && !financed.has(ch.id)),
    );
  }

  async financeCharge(charge: Charge): Promise<void> {
    const patient = this.pickedPatient();
    if (!patient) return;
    this.newRef?.close();
    const created = await openCreditCreate(this.dialog, {
      patientId: patient.id,
      charge: { id: charge.id, description: charge.description, pending: charge.pending },
    });
    if (created) {
      this.snackBar.open('Crédito creado', 'Cerrar', { duration: 3000 });
      await this.reload();
      await openCreditDetail(this.dialog, created.id);
      await this.reload();
    }
  }
}
