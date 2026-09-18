import { DecimalPipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { firstValueFrom } from 'rxjs';

import { TreatmentsService } from '../../../core/services/treatments.service';
import { Treatment } from '../../../core/models/treatment.models';

@Component({
  selector: 'app-treatments',
  standalone: true,
  imports: [
    DecimalPipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatTableModule,
  ],
  templateUrl: './treatments.component.html',
  styleUrl: './treatments.component.scss',
})
export class TreatmentsComponent implements OnInit {
  private readonly treatmentsService = inject(TreatmentsService);
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);

  readonly treatments = signal<Treatment[]>([]);
  readonly saving = signal(false);
  readonly displayedColumns = ['name', 'price', 'status', 'actions'];

  readonly form = this.fb.nonNullable.group({
    name: ['', Validators.required],
    description: [''],
    default_price: [0, [Validators.required, Validators.min(0)]],
  });

  async ngOnInit(): Promise<void> {
    await this.reload();
  }

  async reload(): Promise<void> {
    this.treatments.set(await firstValueFrom(this.treatmentsService.list(true)));
  }

  async submit(): Promise<void> {
    if (this.form.invalid || this.saving()) return;
    this.saving.set(true);
    try {
      await firstValueFrom(this.treatmentsService.create(this.form.getRawValue()));
      this.form.reset({ default_price: 0 });
      this.snackBar.open('Tratamiento agregado al catálogo', 'Cerrar', { duration: 3000 });
      await this.reload();
    } finally {
      this.saving.set(false);
    }
  }

  async toggleActive(treatment: Treatment): Promise<void> {
    await firstValueFrom(this.treatmentsService.update(treatment.id, { is_active: !treatment.is_active }));
    await this.reload();
  }
}
