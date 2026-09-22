import { Component, OnInit, TemplateRef, ViewChild, inject, signal } from '@angular/core';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatMenuModule } from '@angular/material/menu';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { firstValueFrom } from 'rxjs';

import { ClinicService } from '../../../core/services/clinic.service';
import { Professional, Specialty } from '../../../core/models/clinic.models';
import { confirmAction } from '../../../shared/confirm-dialog/confirm-dialog.component';
import { promptText } from '../../../shared/confirm-dialog/prompt-dialog.component';

/** Colores para distinguir a cada profesional en la agenda. Probados sobre el
 *  fondo claro y el oscuro: todos se leen con texto blanco encima. */
export const PROFESSIONAL_COLORS = [
  '#0E7C74', '#2563EB', '#7C3AED', '#C2410C', '#B45309', '#BE185D', '#0F766E', '#4D7C0F',
];

function errorDetail(err: unknown, fallback: string): string {
  const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
  return typeof detail === 'string' ? detail : fallback;
}

@Component({
  selector: 'app-professionals',
  standalone: true,
  imports: [
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatSelectModule,
    MatTableModule,
    MatTooltipModule,
  ],
  templateUrl: './professionals.component.html',
  styleUrl: './professionals.component.scss',
})
export class ProfessionalsComponent implements OnInit {
  private readonly clinicService = inject(ClinicService);
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);
  private readonly dialog = inject(MatDialog);

  @ViewChild('formDialog') formDialog!: TemplateRef<unknown>;
  private dialogRef: MatDialogRef<unknown> | null = null;
  readonly error = signal<string | null>(null);

  readonly professionals = signal<Professional[]>([]);
  readonly specialties = signal<Specialty[]>([]);
  readonly saving = signal(false);
  readonly editing = signal<Professional | null>(null);
  readonly displayedColumns = ['name', 'specialty', 'license', 'status', 'actions'];
  /** La paleta, más el color actual si vino de fuera de ella: si no, el
   *  profesional editado no tendría ningún color marcado. */
  readonly colors = signal<string[]>(PROFESSIONAL_COLORS);

  readonly form = this.fb.nonNullable.group({
    first_name: ['', Validators.required],
    last_name: ['', Validators.required],
    specialty_id: [''],
    license_number: [''],
    color_hex: [PROFESSIONAL_COLORS[0]],
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

  specialtyUses(id: string): number {
    return this.professionals().filter((p) => p.specialty_id === id).length;
  }

  async addSpecialty(): Promise<void> {
    const name = this.newSpecialtyName().trim();
    if (!name) return;
    await firstValueFrom(this.clinicService.createSpecialty(name));
    this.newSpecialtyName.set('');
    this.snackBar.open(`Especialidad "${name}" agregada`, 'Cerrar', { duration: 2500 });
    await this.reload();
  }

  async renameSpecialty(specialty: Specialty): Promise<void> {
    const name = await promptText(this.dialog, {
      title: 'Renombrar especialidad',
      label: 'Nombre',
      initial: specialty.name,
    });
    if (!name || name === specialty.name) return;
    await firstValueFrom(this.clinicService.updateSpecialty(specialty.id, name));
    await this.reload();
  }

  async deleteSpecialty(specialty: Specialty): Promise<void> {
    const ok = await confirmAction(this.dialog, {
      title: `¿Eliminar "${specialty.name}"?`,
      message: 'Es solo una etiqueta: no afecta a citas ni registros.',
      confirmLabel: 'Eliminar',
      danger: true,
    });
    if (!ok) return;
    try {
      await firstValueFrom(this.clinicService.deleteSpecialty(specialty.id));
      await this.reload();
    } catch (err) {
      this.snackBar.open(errorDetail(err, 'No se pudo eliminar'), 'Cerrar', { duration: 4500 });
    }
  }

  open(professional: Professional | null = null): void {
    this.editing.set(professional);
    const current = professional?.color_hex?.toUpperCase();
    this.colors.set(
      current && !PROFESSIONAL_COLORS.includes(current) ? [...PROFESSIONAL_COLORS, current] : PROFESSIONAL_COLORS,
    );
    this.form.reset({
      first_name: professional?.first_name ?? '',
      last_name: professional?.last_name ?? '',
      specialty_id: professional?.specialty_id ?? '',
      license_number: professional?.license_number ?? '',
      color_hex: professional?.color_hex?.toUpperCase() ?? this.nextColor(),
    });
    this.error.set(null);
    this.dialogRef = this.dialog.open(this.formDialog, {
      width: '560px',
      maxWidth: '96vw',
      autoFocus: 'first-tabbable',
      panelClass: 'app-dialog',
    });
  }

  /** Propone un color que nadie use todavía, para que la agenda se distinga sola. */
  private nextColor(): string {
    const used = new Set(this.professionals().map((p) => p.color_hex?.toUpperCase()));
    return PROFESSIONAL_COLORS.find((c) => !used.has(c)) ?? PROFESSIONAL_COLORS[0];
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
      const payload = {
        ...value,
        specialty_id: value.specialty_id || null,
        license_number: value.license_number.trim() || null,
      };
      const editing = this.editing();
      if (editing) {
        await firstValueFrom(this.clinicService.updateProfessional(editing.id, payload));
      } else {
        await firstValueFrom(this.clinicService.createProfessional(payload));
      }
      this.dialogRef?.close();
      this.snackBar.open(editing ? 'Profesional actualizado' : 'Profesional creado', 'Cerrar', { duration: 3000 });
      await this.reload();
    } catch (err) {
      this.error.set(errorDetail(err, 'No se pudo guardar el profesional.'));
    } finally {
      this.saving.set(false);
    }
  }

  async toggleActive(professional: Professional): Promise<void> {
    if (professional.is_active) {
      const ok = await confirmAction(this.dialog, {
        title: `¿Desactivar a ${professional.first_name} ${professional.last_name}?`,
        message: 'Ya no aparecerá al agendar citas nuevas. Sus citas y registros anteriores se conservan.',
        confirmLabel: 'Desactivar',
        danger: true,
      });
      if (!ok) return;
    }
    await firstValueFrom(
      this.clinicService.updateProfessional(professional.id, { is_active: !professional.is_active }),
    );
    this.snackBar.open(professional.is_active ? 'Profesional desactivado' : 'Profesional reactivado', 'Cerrar', {
      duration: 3000,
    });
    await this.reload();
  }

  initials(p: Professional): string {
    return `${p.first_name.charAt(0)}${p.last_name.charAt(0)}`.toUpperCase();
  }
}
