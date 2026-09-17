import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { firstValueFrom } from 'rxjs';

import { ClinicService } from '../../../core/services/clinic.service';
import { Professional, Specialty } from '../../../core/models/clinic.models';

@Component({
  selector: 'app-professionals',
  standalone: true,
  imports: [
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatTableModule,
  ],
  templateUrl: './professionals.component.html',
  styleUrl: './professionals.component.scss',
})
export class ProfessionalsComponent implements OnInit {
  private readonly clinicService = inject(ClinicService);
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);

  readonly professionals = signal<Professional[]>([]);
  readonly specialties = signal<Specialty[]>([]);
  readonly saving = signal(false);
  readonly displayedColumns = ['name', 'specialty', 'license', 'status'];

  readonly form = this.fb.nonNullable.group({
    first_name: ['', Validators.required],
    last_name: ['', Validators.required],
    specialty_id: [''],
    license_number: [''],
  });

  readonly newSpecialtyName = signal('');

  async ngOnInit(): Promise<void> {
    await this.reload();
  }

  async reload(): Promise<void> {
    const [professionals, specialties] = await Promise.all([
      firstValueFrom(this.clinicService.listProfessionals()),
      firstValueFrom(this.clinicService.listSpecialties()),
    ]);
    this.professionals.set(professionals);
    this.specialties.set(specialties);
  }

  specialtyName(id: string | null): string {
    if (!id) return '—';
    return this.specialties().find((s) => s.id === id)?.name ?? '—';
  }

  async addSpecialty(): Promise<void> {
    const name = this.newSpecialtyName().trim();
    if (!name) return;
    await firstValueFrom(this.clinicService.createSpecialty(name));
    this.newSpecialtyName.set('');
    await this.reload();
  }

  async submit(): Promise<void> {
    if (this.form.invalid || this.saving()) return;
    this.saving.set(true);
    try {
      const value = this.form.getRawValue();
      await firstValueFrom(
        this.clinicService.createProfessional({
          ...value,
          specialty_id: value.specialty_id || null,
        }),
      );
      this.form.reset();
      this.snackBar.open('Profesional creado', 'Cerrar', { duration: 3000 });
      await this.reload();
    } finally {
      this.saving.set(false);
    }
  }
}
