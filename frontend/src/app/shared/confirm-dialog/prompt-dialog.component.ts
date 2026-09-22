import { Component, inject } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { firstValueFrom } from 'rxjs';

export interface PromptOptions {
  title: string;
  message?: string;
  label: string;
  initial?: string;
  confirmLabel?: string;
  /** Longitud mínima; los motivos de anulación piden al menos 3 letras. */
  minLength?: number;
  multiline?: boolean;
  danger?: boolean;
}

@Component({
  selector: 'app-prompt-dialog',
  standalone: true,
  imports: [MatDialogModule, MatButtonModule, MatFormFieldModule, MatInputModule, ReactiveFormsModule],
  template: `
    <h2 mat-dialog-title>{{ data.title }}</h2>
    <!-- [formGroup] es lo que convierte ngSubmit en un envío de Angular: sin él,
         el formulario se enviaría como HTML y recargaría la página. -->
    <form [formGroup]="group" (ngSubmit)="submit()">
      <mat-dialog-content>
        @if (data.message) {
          <p class="message">{{ data.message }}</p>
        }
        <mat-form-field appearance="outline" class="field">
          <mat-label>{{ data.label }}</mat-label>
          @if (data.multiline) {
            <textarea matInput [formControl]="control" rows="3" cdkFocusInitial></textarea>
          } @else {
            <input matInput [formControl]="control" cdkFocusInitial />
          }
          @if (control.hasError('required')) {
            <mat-error>Este campo es obligatorio</mat-error>
          } @else if (control.hasError('minlength')) {
            <mat-error>Escriba al menos {{ data.minLength }} caracteres</mat-error>
          }
        </mat-form-field>
      </mat-dialog-content>
      <mat-dialog-actions align="end">
        <button mat-button type="button" mat-dialog-close>Cancelar</button>
        <button mat-flat-button type="submit" [class.danger]="data.danger">
          {{ data.confirmLabel ?? 'Guardar' }}
        </button>
      </mat-dialog-actions>
    </form>
  `,
  styles: [
    `
      .message {
        margin: 0 0 12px;
        line-height: 1.5;
        color: var(--color-ink-soft);
      }

      .field {
        width: 100%;
      }

      .danger {
        --mdc-filled-button-container-color: var(--color-danger);
        --mdc-filled-button-label-text-color: #fff;
      }
    `,
  ],
})
export class PromptDialogComponent {
  readonly data = inject<PromptOptions>(MAT_DIALOG_DATA);
  private readonly ref = inject(MatDialogRef<PromptDialogComponent, string>);

  readonly control = new FormControl(this.data.initial ?? '', {
    nonNullable: true,
    validators: [Validators.required, Validators.minLength(this.data.minLength ?? 1)],
  });
  readonly group = new FormGroup({ value: this.control });

  submit(): void {
    const value = this.control.value.trim();
    if (this.control.invalid || value.length < (this.data.minLength ?? 1)) {
      this.control.markAsTouched();
      // Solo espacios cuenta como vacío, no como "demasiado corto".
      this.control.setErrors(value ? { minlength: true } : { required: true });
      return;
    }
    this.ref.close(value);
  }
}

/** Devuelve el texto escrito, o null si se canceló. */
export async function promptText(dialog: MatDialog, options: PromptOptions): Promise<string | null> {
  const ref = dialog.open(PromptDialogComponent, {
    data: options,
    width: '460px',
    maxWidth: '94vw',
    panelClass: 'app-dialog',
  });
  return (await firstValueFrom(ref.afterClosed())) ?? null;
}

/** Atajo para anular registros clínicos: siempre pide el motivo. */
export function promptVoidReason(dialog: MatDialog, what: string): Promise<string | null> {
  return promptText(dialog, {
    title: `Anular ${what}`,
    message:
      'No se borra: queda en la historia marcado como anulado, con su motivo, la fecha y quién lo anuló.',
    label: 'Motivo de la anulación',
    minLength: 3,
    multiline: true,
    confirmLabel: 'Anular',
    danger: true,
  });
}
