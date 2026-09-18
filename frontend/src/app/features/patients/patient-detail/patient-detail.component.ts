import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { firstValueFrom } from 'rxjs';

import { PatientsService } from '../../../core/services/patients.service';
import { HasPermissionDirective } from '../../../core/auth/has-permission.directive';
import { MedicalHistory, Patient, Sex } from '../../../core/models/patient.models';
import { OdontogramComponent } from '../../odontogram/odontogram.component';
import { TreatmentPlansTabComponent } from '../../treatment-plans/treatment-plans-tab.component';

@Component({
  selector: 'app-patient-detail',
  standalone: true,
  imports: [
    DatePipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatTabsModule,
    HasPermissionDirective,
    OdontogramComponent,
    TreatmentPlansTabComponent,
  ],
  templateUrl: './patient-detail.component.html',
  styleUrl: './patient-detail.component.scss',
})
export class PatientDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly patientsService = inject(PatientsService);
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);

  readonly patient = signal<Patient | null>(null);
  readonly latestHistory = signal<MedicalHistory | null>(null);
  readonly historyVersions = signal<MedicalHistory[]>([]);
  readonly editingDemographics = signal(false);
  readonly editingHistory = signal(false);
  readonly showVersionHistory = signal(false);
  readonly saving = signal(false);

  readonly demographicsForm = this.fb.nonNullable.group({
    first_name: [''],
    last_name: [''],
    national_id: [''],
    birth_date: [''],
    sex: [''],
    phone: [''],
    whatsapp: [''],
    email: [''],
    address: [''],
    city: [''],
    occupation: [''],
    emergency_contact_name: [''],
    emergency_contact_phone: [''],
    notes: [''],
  });

  readonly historyForm = this.fb.nonNullable.group({
    allergies: [''],
    medications: [''],
    medical_conditions: [''],
    surgeries: [''],
    habits: [''],
    vital_signs: [''],
    chief_complaint: [''],
    present_illness_history: [''],
    oral_hygiene: [''],
    dental_habits: [''],
    dental_history: [''],
    extraoral_exam: [''],
    intraoral_exam: [''],
    soft_tissues: [''],
    gums: [''],
    periodontium: [''],
    tmj: [''],
    occlusion: [''],
    observations: [''],
  });

  async ngOnInit(): Promise<void> {
    const id = this.route.snapshot.paramMap.get('id')!;
    await this.loadPatient(id);
    await this.loadHistory(id);
  }

  private async loadPatient(id: string): Promise<void> {
    const patient = await firstValueFrom(this.patientsService.getPatient(id));
    this.patient.set(patient);
    this.demographicsForm.patchValue({
      first_name: patient.first_name,
      last_name: patient.last_name,
      national_id: patient.national_id ?? '',
      birth_date: patient.birth_date ?? '',
      sex: patient.sex ?? '',
      phone: patient.phone ?? '',
      whatsapp: patient.whatsapp ?? '',
      email: patient.email ?? '',
      address: patient.address ?? '',
      city: patient.city ?? '',
      occupation: patient.occupation ?? '',
      emergency_contact_name: patient.emergency_contact_name ?? '',
      emergency_contact_phone: patient.emergency_contact_phone ?? '',
      notes: patient.notes ?? '',
    });
  }

  private async loadHistory(id: string): Promise<void> {
    const latest = await firstValueFrom(this.patientsService.getLatestMedicalHistory(id));
    this.latestHistory.set(latest);
  }

  async loadVersions(): Promise<void> {
    const patient = this.patient();
    if (!patient) return;
    const versions = await firstValueFrom(this.patientsService.listMedicalHistoryVersions(patient.id));
    this.historyVersions.set(versions);
    this.showVersionHistory.set(true);
  }

  startEditingHistory(): void {
    const latest = this.latestHistory();
    this.historyForm.reset({
      allergies: latest?.allergies ?? '',
      medications: latest?.medications ?? '',
      medical_conditions: latest?.medical_conditions ?? '',
      surgeries: latest?.surgeries ?? '',
      habits: latest?.habits ?? '',
      vital_signs: latest?.vital_signs ?? '',
      chief_complaint: latest?.chief_complaint ?? '',
      present_illness_history: latest?.present_illness_history ?? '',
      oral_hygiene: latest?.oral_hygiene ?? '',
      dental_habits: latest?.dental_habits ?? '',
      dental_history: latest?.dental_history ?? '',
      extraoral_exam: latest?.extraoral_exam ?? '',
      intraoral_exam: latest?.intraoral_exam ?? '',
      soft_tissues: latest?.soft_tissues ?? '',
      gums: latest?.gums ?? '',
      periodontium: latest?.periodontium ?? '',
      tmj: latest?.tmj ?? '',
      occlusion: latest?.occlusion ?? '',
      observations: latest?.observations ?? '',
    });
    this.editingHistory.set(true);
  }

  async saveDemographics(): Promise<void> {
    const patient = this.patient();
    if (!patient || this.saving()) return;
    this.saving.set(true);
    try {
      const value = this.demographicsForm.getRawValue();
      const updated = await firstValueFrom(
        this.patientsService.updatePatient(patient.id, {
          ...value,
          sex: (value.sex || null) as Sex | null,
        }),
      );
      this.patient.set(updated);
      this.editingDemographics.set(false);
      this.snackBar.open('Datos del paciente actualizados', 'Cerrar', { duration: 3000 });
    } finally {
      this.saving.set(false);
    }
  }

  async saveHistoryVersion(): Promise<void> {
    const patient = this.patient();
    if (!patient || this.saving()) return;
    this.saving.set(true);
    try {
      const entry = await firstValueFrom(
        this.patientsService.createMedicalHistoryVersion(patient.id, this.historyForm.getRawValue()),
      );
      this.latestHistory.set(entry);
      this.editingHistory.set(false);
      this.snackBar.open('Nueva versión de la historia clínica guardada', 'Cerrar', { duration: 3000 });
    } finally {
      this.saving.set(false);
    }
  }

  async deactivatePatient(): Promise<void> {
    const patient = this.patient();
    if (!patient) return;
    await firstValueFrom(this.patientsService.deactivatePatient(patient.id));
    await this.router.navigate(['/patients']);
  }
}
