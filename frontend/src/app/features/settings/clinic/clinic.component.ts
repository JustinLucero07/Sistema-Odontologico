import { Component, OnInit, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { ClinicService } from '../../../core/services/clinic.service';

@Component({
  selector: 'app-clinic',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatCardModule, MatFormFieldModule, MatInputModule],
  templateUrl: './clinic.component.html',
  styleUrl: './clinic.component.scss',
})
export class ClinicComponent implements OnInit {
  private readonly clinicService = inject(ClinicService);
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);

  readonly saving = signal(false);

  readonly form = this.fb.nonNullable.group({
    name: [''],
    legal_name: [''],
    tax_id: [''],
    address: [''],
    phone: [''],
    email: [''],
    timezone: [''],
    currency: [''],
  });

  async ngOnInit(): Promise<void> {
    const clinic = await firstValueFrom(this.clinicService.getMyClinic());
    this.form.patchValue({
      name: clinic.name,
      legal_name: clinic.legal_name ?? '',
      tax_id: clinic.tax_id ?? '',
      address: clinic.address ?? '',
      phone: clinic.phone ?? '',
      email: clinic.email ?? '',
      timezone: clinic.timezone,
      currency: clinic.currency,
    });
  }

  async submit(): Promise<void> {
    if (this.saving()) return;
    this.saving.set(true);
    try {
      await firstValueFrom(this.clinicService.updateMyClinic(this.form.getRawValue()));
      this.snackBar.open('Datos de la clínica actualizados', 'Cerrar', { duration: 3000 });
    } finally {
      this.saving.set(false);
    }
  }
}
