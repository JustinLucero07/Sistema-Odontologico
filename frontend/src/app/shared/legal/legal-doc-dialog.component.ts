import { Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { firstValueFrom } from 'rxjs';

import { LegalDocument, LegalService } from '../../core/services/legal.service';
import { printLegalDocument } from '../print/privacy-print';

/** Muestra los Términos de uso o el contrato de encargo tal como los sirve
 *  el servidor (el mismo texto que ve la app del celular). */
@Component({
  selector: 'app-legal-doc-dialog',
  standalone: true,
  imports: [MatDialogModule, MatButtonModule, MatIconModule],
  template: `
    @if (doc(); as d) {
      <h2 mat-dialog-title>{{ d.title }}</h2>
      <mat-dialog-content class="doc">
        <span class="version">Versión {{ d.version }}</span>
        @for (s of d.sections; track s.title) {
          <h3>{{ s.title }}</h3>
          @for (p of s.paragraphs; track $index) { <p>{{ p }}</p> }
        }
      </mat-dialog-content>
    } @else {
      <mat-dialog-content><p class="cargando">Cargando…</p></mat-dialog-content>
    }
    <mat-dialog-actions align="end">
      <button mat-button (click)="imprimir()" [disabled]="!doc()"><mat-icon>print</mat-icon>Imprimir</button>
      <button mat-flat-button mat-dialog-close>Cerrar</button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      .doc { max-width: 720px; }
      .version { font-size: 0.78rem; color: var(--color-ink-faint); }
      h3 { margin: 16px 0 4px; font-size: 0.95rem; color: var(--color-primary); }
      p { margin: 0 0 8px; line-height: 1.6; }
      .cargando { color: var(--color-ink-faint); }
    `,
  ],
})
export class LegalDocDialogComponent {
  private readonly legal = inject(LegalService);
  private readonly data = inject<{ code: LegalDocument['code']; acceptance?: string | null }>(MAT_DIALOG_DATA);
  readonly doc = toSignal(this.legal.getDocument(this.data.code));

  async imprimir(): Promise<void> {
    const d = this.doc();
    if (!d) return;
    const c = await firstValueFrom(this.legal.getController());
    printLegalDocument(c, d, this.data.acceptance ?? null);
  }
}

export function openLegalDoc(dialog: MatDialog, code: LegalDocument['code'], acceptance?: string | null): void {
  dialog.open(LegalDocDialogComponent, {
    data: { code, acceptance },
    width: '760px',
    maxWidth: '96vw',
    maxHeight: '90vh',
    panelClass: 'app-dialog',
  });
}
