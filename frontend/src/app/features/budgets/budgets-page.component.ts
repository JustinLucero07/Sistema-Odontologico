import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { PatientListItem } from '../../core/models/patient.models';
import { Budget, BudgetStatus } from '../../core/models/treatment.models';
import { TreatmentPlansService } from '../../core/services/treatment-plans.service';
import { PatientPickerComponent } from '../../shared/patient-picker/patient-picker.component';

const STATUS_LABELS: Record<BudgetStatus, string> = {
  borrador: 'Borrador',
  enviado: 'Enviado',
  visto: 'Visto',
  aceptado: 'Aceptado',
  rechazado: 'Rechazado',
};

const NEXT_STATUS: Partial<Record<BudgetStatus, { next: BudgetStatus; label: string }>> = {
  borrador: { next: 'enviado', label: 'Marcar como enviado' },
  enviado: { next: 'visto', label: 'Marcar como visto' },
  visto: { next: 'aceptado', label: 'Marcar como aceptado' },
};

@Component({
  selector: 'app-budgets-page',
  standalone: true,
  imports: [
    DatePipe,
    DecimalPipe,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatIconModule,
    PatientPickerComponent,
  ],
  templateUrl: './budgets-page.component.html',
  styleUrl: './budgets-page.component.scss',
})
export class BudgetsPageComponent {
  private readonly plansService = inject(TreatmentPlansService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly auth = inject(AuthService);

  readonly statusLabels = STATUS_LABELS;
  readonly nextStatus = NEXT_STATUS;
  readonly canEdit = computed(() => this.auth.hasPermission('budgets:write'));

  readonly selectedPatient = signal<PatientListItem | null>(null);
  readonly budgets = signal<Budget[]>([]);
  readonly loading = signal(false);

  readonly totalAccepted = computed(() =>
    this.budgets()
      .filter((b) => b.status === 'aceptado')
      .reduce((sum, b) => sum + b.total, 0),
  );

  readonly totalPending = computed(() =>
    this.budgets()
      .filter((b) => b.status === 'enviado' || b.status === 'visto')
      .reduce((sum, b) => sum + b.total, 0),
  );

  async selectPatient(patient: PatientListItem): Promise<void> {
    this.selectedPatient.set(patient);
    await this.reload();
  }

  clearSelection(): void {
    this.selectedPatient.set(null);
    this.budgets.set([]);
  }

  async reload(): Promise<void> {
    const patient = this.selectedPatient();
    if (!patient) return;
    this.loading.set(true);
    try {
      this.budgets.set(await firstValueFrom(this.plansService.listBudgets(patient.id)));
    } finally {
      this.loading.set(false);
    }
  }

  async advance(budget: Budget): Promise<void> {
    const next = NEXT_STATUS[budget.status];
    if (!next) return;
    await firstValueFrom(this.plansService.updateBudgetStatus(budget.id, next.next));
    this.snackBar.open(`Presupuesto marcado como ${STATUS_LABELS[next.next].toLowerCase()}`, 'Cerrar', {
      duration: 3000,
    });
    await this.reload();
  }

  async reject(budget: Budget): Promise<void> {
    await firstValueFrom(this.plansService.updateBudgetStatus(budget.id, 'rechazado'));
    await this.reload();
  }

  print(): void {
    window.print();
  }
}
