import { DecimalPipe } from '@angular/common';
import { Component, OnInit, TemplateRef, ViewChild, computed, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, FormControl, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
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
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSlideToggleModule,
    MatTableModule,
    MatTooltipModule,
  ],
  templateUrl: './treatments.component.html',
  styleUrl: './treatments.component.scss',
})
export class TreatmentsComponent implements OnInit {
  private readonly treatmentsService = inject(TreatmentsService);
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);
  private readonly dialog = inject(MatDialog);

  @ViewChild('formDialog') formDialog!: TemplateRef<unknown>;
  private dialogRef: MatDialogRef<unknown> | null = null;

  readonly treatments = signal<Treatment[]>([]);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  /** El tratamiento que se edita, o null cuando el diálogo crea uno nuevo. */
  readonly editing = signal<Treatment | null>(null);
  readonly displayedColumns = ['name', 'price', 'status', 'actions'];

  readonly filter = new FormControl('', { nonNullable: true });
  private readonly filterText = signal('');
  readonly showInactive = signal(false);

  readonly visible = computed(() => {
    const term = this.filterText().trim().toLowerCase();
    return this.treatments().filter(
      (t) => (this.showInactive() || t.is_active) && (!term || t.name.toLowerCase().includes(term)),
    );
  });

  readonly activeCount = computed(() => this.treatments().filter((t) => t.is_active).length);

  readonly form = this.fb.nonNullable.group({
    name: ['', Validators.required],
    description: [''],
    default_price: [0, [Validators.required, Validators.min(0)]],
  });

  constructor() {
    this.filter.valueChanges.subscribe((value) => this.filterText.set(value));
  }

  async ngOnInit(): Promise<void> {
    await this.reload();
  }

  async reload(): Promise<void> {
    this.treatments.set(await firstValueFrom(this.treatmentsService.list(true)));
  }

  open(treatment: Treatment | null = null): void {
    this.editing.set(treatment);
    this.error.set(null);
    this.form.reset({
      name: treatment?.name ?? '',
      description: treatment?.description ?? '',
      default_price: treatment ? Number(treatment.default_price) : 0,
    });
    this.dialogRef = this.dialog.open(this.formDialog, {
      width: '560px',
      maxWidth: '96vw',
      autoFocus: 'first-tabbable',
      panelClass: 'app-dialog',
    });
  }

  async submit(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    if (this.saving()) return;
    this.saving.set(true);
    this.error.set(null);
    try {
      const value = this.form.getRawValue();
      const editing = this.editing();
      if (editing) {
        await firstValueFrom(this.treatmentsService.update(editing.id, value));
        this.snackBar.open('Tratamiento actualizado', 'Cerrar', { duration: 3000 });
      } else {
        await firstValueFrom(this.treatmentsService.create(value));
        this.snackBar.open('Tratamiento agregado al catálogo', 'Cerrar', { duration: 3000 });
      }
      this.dialogRef?.close();
      await this.reload();
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.error.set(typeof detail === 'string' ? detail : 'No se pudo guardar el tratamiento.');
    } finally {
      this.saving.set(false);
    }
  }

  async toggleActive(treatment: Treatment): Promise<void> {
    await firstValueFrom(this.treatmentsService.update(treatment.id, { is_active: !treatment.is_active }));
    this.snackBar.open(
      treatment.is_active ? 'Ya no aparecerá al armar planes nuevos' : 'Tratamiento reactivado',
      'Cerrar',
      { duration: 3000 },
    );
    await this.reload();
  }
}
