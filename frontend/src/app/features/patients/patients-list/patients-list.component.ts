import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder } from '@angular/forms';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, debounceTime, distinctUntilChanged, firstValueFrom } from 'rxjs';

import { PatientsService } from '../../../core/services/patients.service';
import { PatientListItem } from '../../../core/models/patient.models';
import { HasPermissionDirective } from '../../../core/auth/has-permission.directive';
import { openPatientCreateDialog } from '../../../shared/patient-dialog/patient-create-dialog.component';

@Component({
  selector: 'app-patients-list',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatTooltipModule,
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
  private readonly dialog = inject(MatDialog);

  readonly patients = signal<PatientListItem[]>([]);
  readonly loading = signal(true);
  readonly searchControl = this.fb.nonNullable.control('');
  private readonly search$ = new Subject<string>();

  readonly searching = computed(() => this.term().trim().length > 0);
  private readonly term = signal('');

  ngOnInit(): void {
    this.search$.pipe(debounceTime(300), distinctUntilChanged()).subscribe((t) => this.reload(t));
    this.searchControl.valueChanges.subscribe((value) => {
      this.term.set(value);
      this.search$.next(value);
    });
    this.reload();
  }

  async reload(search?: string): Promise<void> {
    this.loading.set(true);
    try {
      this.patients.set(
        await firstValueFrom(this.patientsService.listPatients(search || undefined)),
      );
    } finally {
      this.loading.set(false);
    }
  }

  initials(p: PatientListItem): string {
    return `${p.first_name[0] ?? ''}${p.last_name[0] ?? ''}`.toUpperCase();
  }

  openPatient(patient: PatientListItem): void {
    this.router.navigate(['/patients', patient.id]);
  }

  clearSearch(): void {
    this.searchControl.setValue('');
  }

  async newPatient(): Promise<void> {
    const created = await openPatientCreateDialog(this.dialog);
    if (!created) return;
    this.snackBar.open(`${created.first_name} ${created.last_name} registrado`, 'Cerrar', {
      duration: 3000,
    });
    this.router.navigate(['/patients', created.id]);
  }
}
