import { Component, OnInit, TemplateRef, ViewChild, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { ConsentTemplate } from '../../../core/models/clinical-record.models';
import { ClinicalRecordsService } from '../../../core/services/clinical-records.service';

@Component({
  selector: 'app-consent-templates',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSlideToggleModule,
  ],
  templateUrl: './consent-templates.component.html',
  styleUrl: './consent-templates.component.scss',
})
export class ConsentTemplatesComponent implements OnInit {
  private readonly records = inject(ClinicalRecordsService);
  private readonly fb = inject(FormBuilder);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);

  @ViewChild('formDialog') formDialog!: TemplateRef<unknown>;
  private dialogRef: MatDialogRef<unknown> | null = null;

  readonly templates = signal<ConsentTemplate[]>([]);
  readonly editing = signal<ConsentTemplate | null>(null);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly showRetired = signal(false);
  readonly loading = signal(true);

  readonly visible = computed(() => this.templates().filter((t) => this.showRetired() || t.is_active));
  readonly retiredCount = computed(() => this.templates().filter((t) => !t.is_active).length);

  readonly form = this.fb.nonNullable.group({
    name: ['', Validators.required],
    procedure_type: [''],
    body: ['', Validators.required],
  });

  async ngOnInit(): Promise<void> {
    await this.reload();
  }

  private async reload(): Promise<void> {
    try {
      this.templates.set(await firstValueFrom(this.records.listAllConsentTemplates()));
    } finally {
      this.loading.set(false);
    }
  }

  open(template: ConsentTemplate | null = null): void {
    this.editing.set(template);
    this.error.set(null);
    this.form.reset({
      name: template?.name ?? '',
      procedure_type: template?.procedure_type ?? '',
      body: template?.body ?? '',
    });
    this.dialogRef = this.dialog.open(this.formDialog, {
      width: '720px',
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
    const raw = this.form.getRawValue();
    const payload = { name: raw.name.trim(), procedure_type: raw.procedure_type.trim() || null, body: raw.body };
    const editing = this.editing();
    try {
      if (editing) {
        await firstValueFrom(this.records.updateConsentTemplate(editing.id, { ...payload, is_active: editing.is_active }));
      } else {
        await firstValueFrom(this.records.createConsentTemplate(payload));
      }
      this.dialogRef?.close();
      this.snackBar.open(editing ? 'Plantilla actualizada' : 'Plantilla creada', 'Cerrar', { duration: 3000 });
      await this.reload();
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.error.set(typeof detail === 'string' ? detail : 'No se pudo guardar la plantilla.');
    } finally {
      this.saving.set(false);
    }
  }

  /** Retirar la quita del selector al emitir; lo ya firmado conserva su texto. */
  async toggleActive(template: ConsentTemplate): Promise<void> {
    const { id, ...rest } = template;
    await firstValueFrom(this.records.updateConsentTemplate(id, { ...rest, is_active: !template.is_active }));
    this.snackBar.open(template.is_active ? 'Plantilla retirada' : 'Plantilla restaurada', 'Cerrar', { duration: 3000 });
    await this.reload();
  }

  preview(body: string): string {
    return body.length > 220 ? `${body.slice(0, 220).trimEnd()}…` : body;
  }
}
