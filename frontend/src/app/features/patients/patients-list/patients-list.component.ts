import { Component, OnInit, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { Subject, debounceTime, distinctUntilChanged, firstValueFrom } from 'rxjs';

import { PatientsService } from '../../../core/services/patients.service';
import { PatientListItem, Sex } from '../../../core/models/patient.models';
import { HasPermissionDirective } from '../../../core/auth/has-permission.directive';

@Component({
  selector: 'app-patients-list',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatTableModule,
    HasPermissionDirective,
  ],
  templateUrl: './patients-list.component.html',
  styleUrl: './patients-list.component.scss',
})
export class PatientsListComponent implements OnInit {
  private readonly patientsService = inject(PatientsService);
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);
  private readonly router = inject(Router);

  readonly patients = signal<PatientListItem[]>([]);
  readonly showCreateForm = signal(false);
  readonly saving = signal(false);
  readonly displayedColumns = ['name', 'national_id', 'age', 'phone', 'actions'];

  readonly searchControl = this.fb.nonNullable.control('');
  private readonly search$ = new Subject<string>();

  readonly form = this.fb.nonNullable.group({
    first_name: ['', Validators.required],
    last_name: ['', Validators.required],
    national_id: [''],
    birth_date: [''],
    sex: [''],
    phone: [''],
    whatsapp: [''],
    email: [''],
  });

  ngOnInit(): void {
    this.search$.pipe(debounceTime(300), distinctUntilChanged()).subscribe((term) => this.reload(term));
    this.searchControl.valueChanges.subscribe((value) => this.search$.next(value));
    this.reload();
  }

  async reload(search?: string): Promise<void> {
    const patients = await firstValueFrom(this.patientsService.listPatients(search || undefined));
    this.patients.set(patients);
  }

  openPatient(patient: PatientListItem): void {
    this.router.navigate(['/patients', patient.id]);
  }

  async submit(): Promise<void> {
    if (this.form.invalid || this.saving()) return;
    this.saving.set(true);
    try {
      const value = this.form.getRawValue();
      const created = await firstValueFrom(
        this.patientsService.createPatient({
          ...value,
          national_id: value.national_id || null,
          birth_date: value.birth_date || null,
          sex: (value.sex || null) as Sex | null,
          phone: value.phone || null,
          whatsapp: value.whatsapp || null,
          email: value.email || null,
        }),
      );
      this.form.reset();
      this.showCreateForm.set(false);
      this.snackBar.open('Paciente creado', 'Cerrar', { duration: 3000 });
      await this.reload(this.searchControl.value);
      this.router.navigate(['/patients', created.id]);
    } finally {
      this.saving.set(false);
    }
  }
}
