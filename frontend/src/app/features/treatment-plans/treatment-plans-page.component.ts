import { Component, signal } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

import { PatientListItem } from '../../core/models/patient.models';
import { PatientPickerComponent } from '../../shared/patient-picker/patient-picker.component';
import { TreatmentPlansTabComponent } from './treatment-plans-tab.component';

@Component({
  selector: 'app-treatment-plans-page',
  standalone: true,
  imports: [MatIconModule, PatientPickerComponent, TreatmentPlansTabComponent],
  template: `
    <div class="page">
      <h1>Planes de tratamiento</h1>

      @if (!selectedPatient()) {
        <app-patient-picker
          hint="Busca un paciente para ver sus diagnósticos, planes de tratamiento y presupuestos."
          (selected)="selectedPatient.set($event)"
        ></app-patient-picker>
      } @else {
        <div class="selected-header">
          <button type="button" class="back-button" (click)="selectedPatient.set(null)">
            <mat-icon>arrow_back</mat-icon>
            Buscar otro paciente
          </button>
          <h2>{{ selectedPatient()!.first_name }} {{ selectedPatient()!.last_name }}</h2>
        </div>

        <app-treatment-plans-tab [patientId]="selectedPatient()!.id"></app-treatment-plans-tab>
      }
    </div>
  `,
  styles: [
    `
      .page {
        display: grid;
        gap: 16px;
        max-width: 960px;
      }

      h1 {
        margin: 0;
        font-size: 1.4rem;
      }

      .selected-header {
        display: flex;
        align-items: center;
        gap: 16px;

        h2 {
          margin: 0;
          font-size: 1.15rem;
        }
      }

      .back-button {
        display: flex;
        align-items: center;
        gap: 4px;
        border: none;
        background: none;
        color: var(--color-primary);
        cursor: pointer;
        font-size: 0.85rem;
        padding: 6px 8px;
        border-radius: var(--radius-sm);

        &:hover {
          background: var(--color-primary-soft);
        }
      }
    `,
  ],
})
export class TreatmentPlansPageComponent {
  readonly selectedPatient = signal<PatientListItem | null>(null);
}
