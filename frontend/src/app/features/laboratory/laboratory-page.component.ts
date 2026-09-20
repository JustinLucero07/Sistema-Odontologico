import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
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
import { PatientListItem } from '../../core/models/patient.models';
import {
  LabCatalog,
  LabOrder,
  LabOrderStatus,
  Laboratory,
  nextStatuses,
} from '../../core/models/laboratory.models';
import { LaboratoryService } from '../../core/services/laboratory.service';
import { PatientsService } from '../../core/services/patients.service';

@Component({
  selector: 'app-laboratory-page',
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
  templateUrl: './laboratory-page.component.html',
  styleUrl: './laboratory-page.component.scss',
})
export class LaboratoryPageComponent implements OnInit {
  private readonly lab = inject(LaboratoryService);
  private readonly patients = inject(PatientsService);
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);
  readonly auth = inject(AuthService);

  readonly orders = signal<LabOrder[]>([]);
  readonly laboratories = signal<Laboratory[]>([]);
  readonly catalog = signal<LabCatalog>({ statuses: [], work_types: [] });
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly openOnly = signal(true);

  readonly showOrderForm = signal(false);
  readonly showLabForm = signal(false);
  readonly advancing = signal<LabOrder | null>(null);
  readonly detail = signal<LabOrder | null>(null);
  chosenStatus: LabOrderStatus | '' = '';
  statusNote = '';

  readonly patientResults = signal<PatientListItem[]>([]);
  readonly chosenPatient = signal<PatientListItem | null>(null);

  readonly orderForm = this.fb.nonNullable.group({
    laboratory_id: ['', Validators.required],
    work_type: ['corona', Validators.required],
    description: ['', Validators.required],
    fdi_numbers: [''],
    shade: [''],
    material: [''],
    due_on: [''],
    cost: [''],
    notes: [''],
  });

  readonly labForm = this.fb.nonNullable.group({
    name: ['', Validators.required],
    contact_name: [''],
    phone: [''],
    email: [''],
    default_turnaround_days: [7],
  });

  get canWrite(): boolean {
    return this.auth.hasPermission('laboratory:write');
  }

  readonly overdueCount = computed(
    () => this.orders().filter((o) => o.days_overdue !== null).length,
  );

  async ngOnInit(): Promise<void> {
    this.catalog.set(await firstValueFrom(this.lab.getCatalog()));
    await this.reload();
  }

  private async reload(): Promise<void> {
    this.loading.set(true);
    try {
      const [orders, laboratories] = await Promise.all([
        firstValueFrom(this.lab.listOrders({ openOnly: this.openOnly() })),
        firstValueFrom(this.lab.listLaboratories()),
      ]);
      this.orders.set(orders);
      this.laboratories.set(laboratories);
    } finally {
      this.loading.set(false);
    }
  }

  async toggleOpenOnly(): Promise<void> {
    this.openOnly.set(!this.openOnly());
    await this.reload();
  }

  statusLabel(code: string): string {
    return this.catalog().statuses.find((s) => s.code === code)?.label ?? code;
  }

  workTypeLabel(code: string): string {
    return this.catalog().work_types.find((w) => w.code === code)?.label ?? code;
  }

  async searchPatient(term: string): Promise<void> {
    if (!term.trim()) {
      this.patientResults.set([]);
      return;
    }
    this.patientResults.set(await firstValueFrom(this.patients.listPatients(term)));
  }

  pickPatient(patient: PatientListItem): void {
    this.chosenPatient.set(patient);
    this.patientResults.set([]);
  }

  async submitLab(): Promise<void> {
    if (this.labForm.invalid || this.saving()) return;
    this.saving.set(true);
    try {
      const raw = this.labForm.getRawValue();
      await firstValueFrom(
        this.lab.createLaboratory({
          name: raw.name,
          contact_name: raw.contact_name || null,
          phone: raw.phone || null,
          email: raw.email || null,
          default_turnaround_days: raw.default_turnaround_days || null,
          is_active: true,
        }),
      );
      this.labForm.reset({ default_turnaround_days: 7 });
      this.showLabForm.set(false);
      await this.reload();
      this.snackBar.open('Laboratorio registrado', 'Cerrar', { duration: 3000 });
    } catch (error) {
      this.report(error, 'No se pudo registrar el laboratorio');
    } finally {
      this.saving.set(false);
    }
  }

  async submitOrder(): Promise<void> {
    const patient = this.chosenPatient();
    if (!patient || this.orderForm.invalid || this.saving()) return;
    this.saving.set(true);
    try {
      const raw = this.orderForm.getRawValue();
      await firstValueFrom(
        this.lab.createOrder({
          patient_id: patient.id,
          laboratory_id: raw.laboratory_id,
          work_type: raw.work_type,
          description: raw.description,
          // Typed as "16, 17"; the API wants a list of validated FDI numbers.
          fdi_numbers: raw.fdi_numbers
            .split(',')
            .map((n) => n.trim())
            .filter(Boolean),
          shade: raw.shade || null,
          material: raw.material || null,
          due_on: raw.due_on || null,
          cost: raw.cost ? raw.cost.replace(',', '.') : null,
          notes: raw.notes || null,
        }),
      );
      this.orderForm.reset({ work_type: 'corona' });
      this.chosenPatient.set(null);
      this.showOrderForm.set(false);
      await this.reload();
      this.snackBar.open('Trabajo registrado', 'Cerrar', { duration: 3000 });
    } catch (error) {
      this.report(error, 'No se pudo registrar el trabajo');
    } finally {
      this.saving.set(false);
    }
  }

  /** Only the steps the case can actually take next. Offering the whole list
   *  and letting the server refuse would be a worse way to say the same thing. */
  availableStatuses(order: LabOrder): { code: string; label: string }[] {
    return nextStatuses(order.status).map((code) => ({
      code,
      label: this.statusLabel(code),
    }));
  }

  openAdvance(order: LabOrder): void {
    this.advancing.set(order);
    this.chosenStatus = '';
    this.statusNote = '';
  }

  async submitStatus(): Promise<void> {
    const order = this.advancing();
    if (!order || !this.chosenStatus || this.saving()) return;
    this.saving.set(true);
    try {
      await firstValueFrom(
        this.lab.updateStatus(order.id, this.chosenStatus, this.statusNote || null),
      );
      this.advancing.set(null);
      await this.reload();
      this.snackBar.open('Estado actualizado', 'Cerrar', { duration: 3000 });
    } catch (error) {
      this.report(error, 'No se pudo cambiar el estado');
    } finally {
      this.saving.set(false);
    }
  }

  private report(error: unknown, fallback: string): void {
    const detail = (error as { error?: { detail?: unknown } })?.error?.detail;
    this.snackBar.open(typeof detail === 'string' ? detail : fallback, 'Cerrar', {
      duration: 8000,
    });
  }
}
