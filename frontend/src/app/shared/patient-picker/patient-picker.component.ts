import { Component, EventEmitter, Input, OnInit, Output, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { Subject, debounceTime, distinctUntilChanged, firstValueFrom } from 'rxjs';

import { PatientListItem } from '../../core/models/patient.models';
import { PatientsService } from '../../core/services/patients.service';

/** Search-and-pick a patient. Used by every "direct access" page that needs a
 * patient in context before it can show anything (odontogram, plans, budgets). */
@Component({
  selector: 'app-patient-picker',
  standalone: true,
  imports: [ReactiveFormsModule, MatCardModule, MatFormFieldModule, MatIconModule, MatInputModule],
  templateUrl: './patient-picker.component.html',
  styleUrl: './patient-picker.component.scss',
})
export class PatientPickerComponent implements OnInit {
  @Input() hint = 'Escribe para buscar un paciente.';
  @Output() selected = new EventEmitter<PatientListItem>();

  private readonly patientsService = inject(PatientsService);
  private readonly fb = inject(FormBuilder);

  readonly searchControl = this.fb.nonNullable.control('');
  private readonly search$ = new Subject<string>();

  readonly results = signal<PatientListItem[]>([]);
  readonly searching = signal(false);

  ngOnInit(): void {
    this.search$.pipe(debounceTime(300), distinctUntilChanged()).subscribe((term) => this.search(term));
    this.searchControl.valueChanges.subscribe((value) => this.search$.next(value));
  }

  private async search(term: string): Promise<void> {
    if (!term.trim()) {
      this.results.set([]);
      return;
    }
    this.searching.set(true);
    try {
      this.results.set(await firstValueFrom(this.patientsService.listPatients(term)));
    } finally {
      this.searching.set(false);
    }
  }

  pick(patient: PatientListItem): void {
    this.selected.emit(patient);
    this.results.set([]);
    this.searchControl.setValue('', { emitEvent: false });
  }
}
