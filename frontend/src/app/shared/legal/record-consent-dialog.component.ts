import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { firstValueFrom } from 'rxjs';

import { CONSENT_METHOD_LABELS, ConsentMethod } from '../../core/services/legal.service';

export interface RecordConsentData {
  title: string;
  message: string;
  confirmLabel: string;
  minor: boolean;
}

export interface RecordConsentResult {
  method: ConsentMethod;
  signed_by_name: string | null;
}

/** Pide cómo se obtuvo la decisión del paciente y, si es menor, quién firma. */
@Component({
  selector: 'app-record-consent-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatDialogModule, MatButtonModule, MatFormFieldModule, MatInputModule, MatSelectModule],
  template: `
    <h2 mat-dialog-title>{{ data.title }}</h2>
    <form [formGroup]="form" (ngSubmit)="submit()">
      <mat-dialog-content>
        <p class="message">{{ data.message }}</p>
        <div class="dialog-grid">
          <mat-form-field appearance="outline" class="full">
            <mat-label>Cómo lo manifestó</mat-label>
            <mat-select formControlName="method">
              @for (m of methods; track m.value) {
                <mat-option [value]="m.value">{{ m.label }}</mat-option>
              }
            </mat-select>
          </mat-form-field>
          @if (data.minor) {
            <mat-form-field appearance="outline" class="full">
              <mat-label>Representante legal</mat-label>
              <input matInput formControlName="signed_by_name" placeholder="Nombre y parentesco" />
              <mat-error>El paciente es menor: indique quién lo representa</mat-error>
            </mat-form-field>
          }
        </div>
      </mat-dialog-content>
      <mat-dialog-actions align="end">
        <button mat-button type="button" mat-dialog-close>Cancelar</button>
        <button mat-flat-button type="submit">{{ data.confirmLabel }}</button>
      </mat-dialog-actions>
    </form>
  `,
  styles: [`.message { margin: 0 0 12px; line-height: 1.5; color: var(--color-ink-soft); }`],
})
export class RecordConsentDialogComponent {
  readonly data = inject<RecordConsentData>(MAT_DIALOG_DATA);
  private readonly ref = inject(MatDialogRef<RecordConsentDialogComponent, RecordConsentResult>);
  readonly methods = Object.entries(CONSENT_METHOD_LABELS).map(([value, label]) => ({
    value: value as ConsentMethod,
    label,
  }));

  readonly form = inject(FormBuilder).nonNullable.group({
    method: ['firma_presencial' as ConsentMethod],
    signed_by_name: ['', this.data.minor ? Validators.required : []],
  });

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const v = this.form.getRawValue();
    this.ref.close({ method: v.method, signed_by_name: v.signed_by_name.trim() || null });
  }
}

export function openRecordConsent(dialog: MatDialog, data: RecordConsentData): Promise<RecordConsentResult | undefined> {
  return firstValueFrom(
    dialog
      .open(RecordConsentDialogComponent, { data, width: '460px', maxWidth: '94vw', panelClass: 'app-dialog' })
      .afterClosed(),
  );
}
