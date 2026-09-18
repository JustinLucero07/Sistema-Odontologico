import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { Subject, debounceTime, distinctUntilChanged, firstValueFrom } from 'rxjs';

import { PatientListItem } from '../../../core/models/patient.models';
import { PatientsService } from '../../../core/services/patients.service';
import { OdontogramComponent } from '../odontogram.component';

@Component({
  selector: 'app-odontogram-search',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    OdontogramComponent,
  ],
  templateUrl: './odontogram-search.component.html',
  styleUrl: './odontogram-search.component.scss',
})
export class OdontogramSearchComponent implements OnInit {
  private readonly patientsService = inject(PatientsService);
  private readonly fb = inject(FormBuilder);

  readonly searchControl = this.fb.nonNullable.control('');
  private readonly search$ = new Subject<string>();

  readonly results = signal<PatientListItem[]>([]);
  readonly selectedPatient = signal<PatientListItem | null>(null);

  ngOnInit(): void {
    this.search$.pipe(debounceTime(300), distinctUntilChanged()).subscribe((term) => this.search(term));
    this.searchControl.valueChanges.subscribe((value) => this.search$.next(value));
  }

  private async search(term: string): Promise<void> {
    if (!term.trim()) {
      this.results.set([]);
      return;
    }
    const results = await firstValueFrom(this.patientsService.listPatients(term));
    this.results.set(results);
  }

  selectPatient(patient: PatientListItem): void {
    this.selectedPatient.set(patient);
    this.results.set([]);
    this.searchControl.setValue('', { emitEvent: false });
  }

  clearSelection(): void {
    this.selectedPatient.set(null);
  }
}
