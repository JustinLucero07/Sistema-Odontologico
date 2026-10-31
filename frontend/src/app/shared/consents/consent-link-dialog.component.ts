import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { Consent, ConsentSignLink } from '../../core/models/clinical-record.models';
import { ClinicalRecordsService } from '../../core/services/clinical-records.service';

export interface ConsentLinkData {
  consent: Consent;
  patientName: string;
  phone: string | null;
  email: string | null;
}

/** Firma a distancia: genera un enlace que el paciente abre en su teléfono
 *  para leer y firmar. El enlace se ve una sola vez (solo se guarda su huella). */
@Component({
  selector: 'app-consent-link-dialog',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatDialogModule, MatIconModule],
  template: `
    <h2 mat-dialog-title>Enviar para firmar</h2>
    <mat-dialog-content>
      <p>El paciente abre el enlace en su teléfono, lee <b>{{ data.consent.title }}</b> y firma con el dedo. No necesita cuenta. El enlace vence en 7 días y sirve una sola vez.</p>
      @if (link(); as l) {
        <div class="link"><code>{{ l.url }}</code></div>
        <p class="muted">Vence el {{ l.expires_at | date: 'dd/MM/yyyy HH:mm' }}.
          @if (l.emailed) { Enviado a {{ data.email }}. }
          @if (l.email_error) { <span class="bad">{{ l.email_error }}</span> }
        </p>
      } @else {
        <p class="muted">Al generar un enlace nuevo, el anterior deja de funcionar.</p>
      }
    </mat-dialog-content>
    <mat-dialog-actions>
      @if (link(); as l) {
        <button mat-button (click)="copy(l.url)"><mat-icon>content_copy</mat-icon>Copiar</button>
        @if (data.phone) {
          <a mat-button [href]="whatsapp(l.url)" target="_blank" rel="noopener"><mat-icon>chat</mat-icon>WhatsApp</a>
        }
        <span class="spacer"></span>
        <button mat-flat-button mat-dialog-close>Listo</button>
      } @else {
        <button mat-button mat-dialog-close>Cancelar</button>
        <span class="spacer"></span>
        @if (data.email) {
          <button mat-stroked-button (click)="generate(true)" [disabled]="busy()"><mat-icon>mail</mat-icon>Generar y enviar por correo</button>
        }
        <button mat-flat-button (click)="generate(false)" [disabled]="busy()"><mat-icon>link</mat-icon>Generar enlace</button>
      }
    </mat-dialog-actions>
  `,
  styles: [
    `
      .link { padding: 12px; border-radius: 12px; background: var(--glass-field-bg); border: 1px solid var(--color-border); word-break: break-all; }
      .muted { color: var(--color-ink-faint); font-size: 0.86rem; }
      .bad { color: var(--color-danger); }
      .spacer { flex: 1; }
      mat-dialog-actions { flex-wrap: wrap; }
    `,
  ],
})
export class ConsentLinkDialogComponent {
  readonly data = inject<ConsentLinkData>(MAT_DIALOG_DATA);
  private readonly service = inject(ClinicalRecordsService);
  private readonly snackBar = inject(MatSnackBar);
  readonly link = signal<ConsentSignLink | null>(null);
  readonly busy = signal(false);

  async generate(sendEmail: boolean): Promise<void> {
    this.busy.set(true);
    try {
      this.link.set(await firstValueFrom(this.service.consentSignLink(this.data.consent.id, sendEmail)));
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.snackBar.open(typeof detail === 'string' ? detail : 'No se pudo generar el enlace.', 'Cerrar', { duration: 6000 });
    } finally {
      this.busy.set(false);
    }
  }

  async copy(url: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(url);
      this.snackBar.open('Enlace copiado', 'Cerrar', { duration: 2500 });
    } catch {
      this.snackBar.open('El navegador no permitió copiar', 'Cerrar', { duration: 4000 });
    }
  }

  whatsapp(url: string): string {
    let n = (this.data.phone ?? '').replace(/\D/g, '');
    if (n.length === 10 && n.startsWith('0')) n = '593' + n.slice(1);
    const texto = `Hola ${this.data.patientName}, le enviamos el consentimiento «${this.data.consent.title}» para que lo lea y lo firme desde su teléfono: ${url}`;
    return `https://wa.me/${n}?text=${encodeURIComponent(texto)}`;
  }
}

export function openConsentLink(dialog: MatDialog, data: ConsentLinkData): Promise<void> {
  return firstValueFrom(
    dialog.open(ConsentLinkDialogComponent, { data, width: '560px', maxWidth: '96vw', panelClass: 'app-dialog' }).afterClosed(),
  );
}
