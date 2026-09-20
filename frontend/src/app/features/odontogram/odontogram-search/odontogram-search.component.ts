import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { firstValueFrom } from 'rxjs';

import { PatientListItem } from '../../../core/models/patient.models';
import { PatientsService } from '../../../core/services/patients.service';
import { PatientPickerComponent } from '../../../shared/patient-picker/patient-picker.component';
import { OdontogramComponent } from '../odontogram.component';

@Component({
  selector: 'app-odontogram-search',
  standalone: true,
  imports: [MatIconModule, PatientPickerComponent, OdontogramComponent],
  templateUrl: './odontogram-search.component.html',
  styleUrl: './odontogram-search.component.scss',
})
export class OdontogramSearchComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly patientsService = inject(PatientsService);

  readonly selectedPatient = signal<PatientListItem | null>(null);

  constructor() {
    // Lets the global search jump straight to a patient's odontogram.
    const patientId = this.route.snapshot.queryParamMap.get('patient');
    if (patientId) void this.preselect(patientId);
  }

  private async preselect(patientId: string): Promise<void> {
    const patient = await firstValueFrom(this.patientsService.getPatient(patientId));
    this.selectedPatient.set({
      id: patient.id,
      first_name: patient.first_name,
      last_name: patient.last_name,
      national_id: patient.national_id,
      age: patient.age,
      phone: patient.phone,
      whatsapp: patient.whatsapp,
    });
  }

  select(patient: PatientListItem): void {
    this.selectedPatient.set(patient);
  }

  clearSelection(): void {
    this.selectedPatient.set(null);
  }
}
