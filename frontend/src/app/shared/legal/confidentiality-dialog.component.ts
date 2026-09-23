import { Component, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { LegalService } from '../../core/services/legal.service';
import { printConfidentialityAgreement } from '../print/privacy-print';
import { LegalSection, confidentialityAgreement } from './legal-texts';

/**
 * Acuerdo de confidencialidad que el personal acepta antes de trabajar con
 * datos de pacientes. No se puede cerrar sin decidir: aceptar, o salir.
 */
@Component({
  selector: 'app-confidentiality-dialog',
  standalone: true,
  imports: [MatButtonModule, MatCheckboxModule, MatDialogModule, MatIconModule],
  template: `
    <div class="head">
      <span class="icon"><mat-icon>shield_person</mat-icon></span>
      <div>
        <h2>Acuerdo de confidencialidad</h2>
        <p>Antes de continuar, lea y acepte cómo se protegen los datos de los pacientes.</p>
      </div>
    </div>
    <mat-dialog-content>
      @for (section of sections(); track section.title) {
        <h3>{{ section.title }}</h3>
        @for (p of section.paragraphs; track $index) {
          <p>{{ p }}</p>
        }
      }
      <mat-checkbox class="accept" [checked]="read()" (change)="read.set($event.checked)">
        He leído el acuerdo y me comprometo a cumplirlo.
      </mat-checkbox>
      @if (error()) {
        <p class="dialog-error">{{ error() }}</p>
      }
    </mat-dialog-content>
    <mat-dialog-actions>
      <button mat-button type="button" (click)="print()">
        <mat-icon>print</mat-icon>
        Imprimir
      </button>
      <span class="spacer"></span>
      <button mat-button type="button" (click)="logout()">Salir</button>
      <button mat-flat-button type="button" [disabled]="!read() || saving()" (click)="accept()">
        {{ saving() ? 'Guardando…' : 'Aceptar y continuar' }}
      </button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      .head { display: flex; gap: 14px; align-items: flex-start; padding: 22px 24px 6px; }
      .head h2 { margin: 0; font-size: 1.2rem; }
      .head p { margin: 2px 0 0; font-size: 0.84rem; color: var(--color-ink-soft); }
      .icon {
        display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
        width: 44px; height: 44px; border-radius: 14px;
        background: var(--color-primary-soft); color: var(--color-primary);
      }
      h3 { margin: 14px 0 4px; font-size: 0.9rem; color: var(--color-primary); }
      p { margin: 0 0 6px; line-height: 1.55; font-size: 0.88rem; color: var(--color-ink); }
      .accept { display: block; margin-top: 16px; font-weight: 600; }
      .spacer { flex: 1; }
      mat-dialog-actions { padding: 8px 20px 18px; }
    `,
  ],
})
export class ConfidentialityDialogComponent {
  private readonly legal = inject(LegalService);
  private readonly auth = inject(AuthService);
  private readonly ref = inject(MatDialogRef<ConfidentialityDialogComponent>);

  readonly sections = signal<LegalSection[]>([]);
  readonly read = signal(false);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);

  constructor() {
    firstValueFrom(this.legal.getController()).then((c) => this.sections.set(confidentialityAgreement(c)));
  }

  async accept(): Promise<void> {
    this.saving.set(true);
    this.error.set(null);
    try {
      await firstValueFrom(this.legal.acceptConfidentiality());
      await this.auth.loadCurrentUser();
      this.ref.close(true);
    } catch {
      this.error.set('No se pudo registrar la aceptación. Intente de nuevo.');
    } finally {
      this.saving.set(false);
    }
  }

  async print(): Promise<void> {
    const controller = await firstValueFrom(this.legal.getController());
    const user = this.auth.currentUser();
    printConfidentialityAgreement(controller, user ? `${user.first_name} ${user.last_name}` : '');
  }

  async logout(): Promise<void> {
    this.ref.close(false);
    await this.auth.logout();
  }
}
