import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, Input, OnChanges, TemplateRef, ViewChild, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { HasPermissionDirective } from '../../core/auth/has-permission.directive';
import {
  Budget,
  BudgetStatus,
  Diagnosis,
  Treatment,
  TreatmentPlan,
  TreatmentPlanItem,
  TreatmentPlanItemStatus,
} from '../../core/models/treatment.models';
import { LegalService } from '../../core/services/legal.service';
import { PatientsService } from '../../core/services/patients.service';
import { TreatmentPlansService } from '../../core/services/treatment-plans.service';
import { printBudget } from '../../shared/print/budget-print';
import { promptText, promptVoidReason } from '../../shared/confirm-dialog/prompt-dialog.component';
import { TreatmentsService } from '../../core/services/treatments.service';

const STATUS_LABELS: Record<TreatmentPlanItemStatus, string> = {
  propuesto: 'Propuesto',
  aprobado: 'Aprobado',
  en_progreso: 'En progreso',
  completado: 'Completado',
  cancelado: 'Cancelado',
  rechazado: 'Rechazado',
};

const BUDGET_STATUS_LABELS: Record<BudgetStatus, string> = {
  borrador: 'Borrador',
  enviado: 'Enviado',
  visto: 'Visto',
  aceptado: 'Aceptado',
  rechazado: 'Rechazado',
};

const BUDGET_NEXT_STATUS: Partial<Record<BudgetStatus, { next: BudgetStatus; label: string }>> = {
  borrador: { next: 'enviado', label: 'Marcar como enviado' },
  enviado: { next: 'visto', label: 'Marcar como visto' },
  visto: { next: 'aceptado', label: 'Marcar como aceptado' },
};

@Component({
  selector: 'app-treatment-plans-tab',
  standalone: true,
  imports: [
    DatePipe,
    DecimalPipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatDialogModule,
    MatTooltipModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule,
    HasPermissionDirective,
  ],
  templateUrl: './treatment-plans-tab.component.html',
  styleUrl: './treatment-plans-tab.component.scss',
})
export class TreatmentPlansTabComponent implements OnChanges {
  @Input({ required: true }) patientId!: string;

  private readonly plansService = inject(TreatmentPlansService);
  private readonly treatmentsService = inject(TreatmentsService);
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);
  private readonly auth = inject(AuthService);
  private readonly legalService = inject(LegalService);
  private readonly patientsService = inject(PatientsService);
  private readonly dialog = inject(MatDialog);

  @ViewChild('itemDialog') itemDialog!: TemplateRef<unknown>;
  @ViewChild('diagnosisDialog') private diagnosisDialog!: TemplateRef<unknown>;
  @ViewChild('planDialog') private planDialog!: TemplateRef<unknown>;
  @ViewChild('addItemDialog') private addItemDialog!: TemplateRef<unknown>;
  private formRef: MatDialogRef<unknown> | null = null;
  private itemDialogRef: MatDialogRef<unknown> | null = null;
  /** Ítem que se edita en el diálogo, con el plan al que pertenece. */
  readonly editingItem = signal<{ planId: string; item: TreatmentPlanItem } | null>(null);
  readonly showVoided = signal(false);

  readonly editItemForm = this.fb.nonNullable.group({
    price: [0, [Validators.required, Validators.min(0)]],
    discount: [0, [Validators.min(0)]],
    fdi_number: [''],
    surface: [''],
    notes: [''],
  });

  readonly canEditItems = computed(() => this.auth.hasPermission('treatments:write'));

  readonly statusLabels = STATUS_LABELS;
  readonly budgetStatusLabels = BUDGET_STATUS_LABELS;
  readonly budgetNextStatus = BUDGET_NEXT_STATUS;
  readonly statusOptions = Object.keys(STATUS_LABELS) as TreatmentPlanItemStatus[];

  readonly diagnoses = signal<Diagnosis[]>([]);
  readonly plans = signal<TreatmentPlan[]>([]);
  readonly budgets = signal<Budget[]>([]);
  readonly catalog = signal<Treatment[]>([]);

  readonly addingItemToPlan = signal<string | null>(null);
  readonly saving = signal(false);

  readonly diagnosisForm = this.fb.nonNullable.group({
    fdi_number: [''],
    description: ['', Validators.required],
  });

  readonly planForm = this.fb.nonNullable.group({
    title: ['Plan de tratamiento', Validators.required],
  });

  readonly itemForm = this.fb.nonNullable.group({
    treatment_id: ['', Validators.required],
    fdi_number: [''],
    price: [0, [Validators.required, Validators.min(0)]],
    discount: [0, [Validators.min(0)]],
  });

  async ngOnChanges(): Promise<void> {
    if (this.patientId) await this.reload();
  }

  async reload(): Promise<void> {
    const [diagnoses, plans, budgets, catalog] = await Promise.all([
      firstValueFrom(this.plansService.listDiagnoses(this.patientId)),
      firstValueFrom(this.plansService.listPlans(this.patientId)),
      firstValueFrom(this.plansService.listBudgets(this.patientId)),
      firstValueFrom(this.treatmentsService.list()),
    ]);
    this.diagnoses.set(diagnoses);
    this.plans.set(plans);
    this.budgets.set(budgets);
    this.catalog.set(catalog);
  }

  budgetsForPlan(planId: string): Budget[] {
    return this.budgets().filter((b) => b.treatment_plan_id === planId);
  }

  treatmentName(id: string): string {
    return this.catalog().find((t) => t.id === id)?.name ?? '';
  }

  onTreatmentSelected(treatmentId: string): void {
    const treatment = this.catalog().find((t) => t.id === treatmentId);
    if (treatment) this.itemForm.patchValue({ price: treatment.default_price });
  }

  async submitDiagnosis(): Promise<void> {
    if (this.diagnosisForm.invalid || this.saving()) return;
    this.saving.set(true);
    try {
      const value = this.diagnosisForm.getRawValue();
      await firstValueFrom(
        this.plansService.createDiagnosis(this.patientId, {
          fdi_number: value.fdi_number || null,
          description: value.description,
        }),
      );
      this.diagnosisForm.reset();
      this.closeFormDialog();
      this.snackBar.open('Diagnóstico registrado', 'Cerrar', { duration: 3000 });
      await this.reload();
    } finally {
      this.saving.set(false);
    }
  }

  async submitNewPlan(): Promise<void> {
    if (this.planForm.invalid || this.saving()) return;
    this.saving.set(true);
    try {
      await firstValueFrom(
        this.plansService.createPlan(this.patientId, { title: this.planForm.getRawValue().title, items: [] }),
      );
      this.planForm.reset({ title: 'Plan de tratamiento' });
      this.closeFormDialog();
      this.snackBar.open('Plan de tratamiento creado', 'Cerrar', { duration: 3000 });
      await this.reload();
    } finally {
      this.saving.set(false);
    }
  }

  /** Los formularios de alta se abren en una ventana emergente. */
  openForm(kind: 'diagnosis' | 'plan' | 'item'): void {
    const template = { diagnosis: this.diagnosisDialog, plan: this.planDialog, item: this.addItemDialog }[kind];
    this.formRef?.close();
    const ref = this.dialog.open(template, {
      width: kind === 'item' ? '620px' : '520px',
      maxWidth: '96vw',
      autoFocus: 'first-tabbable',
      panelClass: 'app-dialog',
    });
    this.formRef = ref;
    ref.afterClosed().subscribe(() => {
      if (this.formRef === ref) this.formRef = null;
      if (kind === 'item') this.addingItemToPlan.set(null);
    });
  }

  private closeFormDialog(): void {
    this.formRef?.close();
    this.formRef = null;
  }

  startAddingItem(planId: string): void {
    this.addingItemToPlan.set(planId);
    this.openForm('item');
    this.itemForm.reset({ price: 0, discount: 0 });
  }

  async submitItem(planId: string): Promise<void> {
    if (this.itemForm.invalid || this.saving()) return;
    this.saving.set(true);
    try {
      const value = this.itemForm.getRawValue();
      await firstValueFrom(
        this.plansService.addItem(planId, {
          treatment_id: value.treatment_id,
          fdi_number: value.fdi_number || null,
          price: value.price,
          discount: value.discount,
        }),
      );
      this.closeFormDialog();
      this.snackBar.open('Ítem agregado al plan', 'Cerrar', { duration: 3000 });
      await this.reload();
    } finally {
      this.saving.set(false);
    }
  }

  // ---- Correcciones ---------------------------------------------------------

  readonly visibleDiagnoses = computed(() =>
    this.diagnoses().filter((d) => this.showVoided() || !d.voided_at),
  );
  readonly voidedCount = computed(() => this.diagnoses().filter((d) => d.voided_at).length);

  async voidDiagnosis(diagnosis: Diagnosis): Promise<void> {
    const reason = await promptVoidReason(this.dialog, 'diagnóstico');
    if (!reason) return;
    try {
      await firstValueFrom(this.plansService.voidDiagnosis(this.patientId, diagnosis.id, reason));
      this.snackBar.open('Diagnóstico anulado', 'Cerrar', { duration: 3000 });
      await this.reload();
    } catch {
      this.snackBar.open('No se pudo anular el diagnóstico', 'Cerrar', { duration: 3500 });
    }
  }

  async renamePlan(plan: TreatmentPlan): Promise<void> {
    const title = await promptText(this.dialog, {
      title: 'Renombrar plan',
      label: 'Título del plan',
      initial: plan.title,
    });
    if (!title || title === plan.title) return;
    await firstValueFrom(this.plansService.updatePlan(plan.id, { title, notes: plan.notes }));
    await this.reload();
  }

  editItem(planId: string, item: TreatmentPlanItem): void {
    this.editingItem.set({ planId, item });
    this.editItemForm.reset({
      price: Number(item.price),
      discount: Number(item.discount),
      fdi_number: item.fdi_number ?? '',
      surface: item.surface ?? '',
      notes: item.notes ?? '',
    });
    this.itemDialogRef = this.dialog.open(this.itemDialog, {
      width: '520px',
      maxWidth: '96vw',
      autoFocus: 'first-tabbable',
      panelClass: 'app-dialog',
    });
  }

  async saveItem(): Promise<void> {
    const target = this.editingItem();
    if (!target) return;
    if (this.editItemForm.invalid) {
      this.editItemForm.markAllAsTouched();
      return;
    }
    const raw = this.editItemForm.getRawValue();
    if (raw.discount > raw.price) {
      this.editItemForm.controls.discount.setErrors({ max: true });
      return;
    }
    this.saving.set(true);
    try {
      await firstValueFrom(
        this.plansService.updateItem(target.planId, target.item.id, {
          price: raw.price,
          discount: raw.discount,
          fdi_number: raw.fdi_number.trim() || null,
          surface: raw.surface.trim() || null,
          notes: raw.notes.trim() || null,
        }),
      );
      this.itemDialogRef?.close();
      this.snackBar.open('Tratamiento actualizado', 'Cerrar', { duration: 3000 });
      await this.reload();
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.snackBar.open(typeof detail === 'string' ? detail : 'No se pudo guardar', 'Cerrar', { duration: 4000 });
    } finally {
      this.saving.set(false);
    }
  }

  async changeItemStatus(planId: string, itemId: string, status: TreatmentPlanItemStatus): Promise<void> {
    await firstValueFrom(this.plansService.updateItemStatus(planId, itemId, status));
    await this.reload();
  }

  async generateBudget(planId: string): Promise<void> {
    await firstValueFrom(this.plansService.createBudget(this.patientId, { treatment_plan_id: planId }));
    this.snackBar.open('Presupuesto generado a partir del plan', 'Cerrar', { duration: 3000 });
    await this.reload();
  }

  async advanceBudgetStatus(budget: Budget): Promise<void> {
    const next = BUDGET_NEXT_STATUS[budget.status];
    if (!next) return;
    await firstValueFrom(this.plansService.updateBudgetStatus(budget.id, next.next));
    await this.reload();
  }

  async rejectBudget(budget: Budget): Promise<void> {
    await firstValueFrom(this.plansService.updateBudgetStatus(budget.id, 'rechazado'));
    await this.reload();
  }

  /** Prints the budget as its own clean document rather than the whole page. */
  async printBudget(budget: Budget, planTitle: string): Promise<void> {
    try {
      const [clinic, patient] = await Promise.all([
        firstValueFrom(this.legalService.getController()),
        firstValueFrom(this.patientsService.getPatient(this.patientId)),
      ]);
      printBudget(budget, clinic, `${patient.first_name} ${patient.last_name}`, planTitle);
    } catch {
      this.snackBar.open('No se pudo preparar el presupuesto para imprimir', 'Cerrar', {
        duration: 4000,
      });
    }
  }
}
