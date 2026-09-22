import { Component, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { firstValueFrom } from 'rxjs';

export interface ConfirmOptions {
  title: string;
  message: string;
  confirmLabel?: string;
  /** Pinta el botón de confirmar en rojo: para lo que no se puede deshacer. */
  danger?: boolean;
}

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [MatDialogModule, MatButtonModule],
  template: `
    <h2 mat-dialog-title>{{ data.title }}</h2>
    <mat-dialog-content>
      <p class="message">{{ data.message }}</p>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button [mat-dialog-close]="false">Cancelar</button>
      <button mat-flat-button [class.danger]="data.danger" [mat-dialog-close]="true" cdkFocusInitial>
        {{ data.confirmLabel ?? 'Confirmar' }}
      </button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      .message {
        margin: 0;
        line-height: 1.5;
        color: var(--color-ink-soft);
      }

      .danger {
        --mdc-filled-button-container-color: var(--color-danger, #c0392b);
        --mdc-filled-button-label-text-color: #fff;
      }
    `,
  ],
})
export class ConfirmDialogComponent {
  readonly data = inject<ConfirmOptions>(MAT_DIALOG_DATA);
}

/** Resuelve true solo si se pulsó confirmar; cerrar con Esc o fuera cuenta como no. */
export async function confirmAction(dialog: MatDialog, options: ConfirmOptions): Promise<boolean> {
  const ref = dialog.open(ConfirmDialogComponent, {
    data: options,
    width: '420px',
    maxWidth: '94vw',
    panelClass: 'app-dialog',
  });
  return (await firstValueFrom(ref.afterClosed())) === true;
}
