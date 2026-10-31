import { Component, ViewChild, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { firstValueFrom } from 'rxjs';

import { Consent } from '../../core/models/clinical-record.models';
import { ClinicalRecordsService } from '../../core/services/clinical-records.service';
import { SignaturePadComponent } from './signature-pad.component';

export interface ConsentSignData {
  consent: Consent;
  patientName: string;
  patientIdNumber: string | null;
}

export const RELATIONSHIPS = ['Paciente', 'Madre', 'Padre', 'Tutor legal', 'Cónyuge', 'Hijo/a', 'Otro representante'];

/** Firma presencial: el paciente (o su representante) firma en la pantalla,
 *  y opcionalmente el profesional y un testigo. */
@Component({
  selector: 'app-consent-sign-dialog',
  standalone: true,
  imports: [FormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatIconModule, MatInputModule, MatSelectModule, MatSlideToggleModule, SignaturePadComponent],
  template: `
    <h2 mat-dialog-title>Firmar consentimiento</h2>
    <mat-dialog-content>
      <p class="title">{{ data.consent.title }}</p>
      <details class="read">
        <summary>Leer el texto completo antes de firmar</summary>
        <p>{{ data.consent.body }}</p>
      </details>

      <div class="grid">
        <mat-form-field appearance="outline">
          <mat-label>Quién firma</mat-label>
          <mat-select [(ngModel)]="relationship" (selectionChange)="onRelationship()">
            @for (r of relationships; track r) { <mat-option [value]="r">{{ r }}</mat-option> }
          </mat-select>
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Nombre completo</mat-label>
          <input matInput [(ngModel)]="name" maxlength="200" />
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Cédula</mat-label>
          <input matInput [(ngModel)]="idNumber" maxlength="20" />
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Testigo (opcional)</mat-label>
          <input matInput [(ngModel)]="witness" maxlength="200" />
        </mat-form-field>
      </div>

      <app-signature-pad #patientPad [label]="relationship === 'Paciente' ? 'Firma del paciente' : 'Firma del representante'" />

      <mat-slide-toggle [(ngModel)]="withProfessional" class="toggle">Agregar la firma del profesional</mat-slide-toggle>
      @if (withProfessional) {
        <app-signature-pad #professionalPad label="Firma del profesional" placeholder="Firma del profesional" />
      }

      @if (error()) { <p class="error"><mat-icon>error_outline</mat-icon>{{ error() }}</p> }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>Cancelar</button>
      <button mat-flat-button (click)="save()" [disabled]="saving() || !name.trim()"><mat-icon>draw</mat-icon>{{ saving() ? 'Guardando…' : 'Firmar' }}</button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      .title { font-weight: 700; margin: 0 0 6px; }
      .read { margin-bottom: 14px; font-size: 0.86rem; summary { cursor: pointer; color: var(--color-primary); }
        p { white-space: pre-line; max-height: 220px; overflow: auto; padding: 10px; border-radius: 10px; background: var(--glass-field-bg); } }
      .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0 12px; }
      .toggle { display: block; margin: 14px 0 10px; }
      .error { display: flex; gap: 6px; align-items: center; color: var(--color-danger); }
    `,
  ],
})
export class ConsentSignDialogComponent {
  readonly data = inject<ConsentSignData>(MAT_DIALOG_DATA);
  private readonly ref = inject(MatDialogRef<ConsentSignDialogComponent, Consent>);
  private readonly service = inject(ClinicalRecordsService);

  @ViewChild('patientPad') patientPad!: SignaturePadComponent;
  @ViewChild('professionalPad') professionalPad?: SignaturePadComponent;

  readonly relationships = RELATIONSHIPS;
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  relationship = 'Paciente';
  name = this.data.patientName;
  idNumber = this.data.patientIdNumber ?? '';
  witness = '';
  withProfessional = false;

  onRelationship(): void {
    // Si firma un representante, sus datos son otros: se piden de nuevo.
    if (this.relationship === 'Paciente') {
      this.name = this.data.patientName;
      this.idNumber = this.data.patientIdNumber ?? '';
    } else if (this.name === this.data.patientName) {
      this.name = '';
      this.idNumber = '';
    }
  }

  async save(): Promise<void> {
    const firma = this.patientPad.dataUrl();
    if (!firma) {
      this.error.set('Falta la firma: dibújela en el recuadro.');
      return;
    }
    this.error.set(null);
    this.saving.set(true);
    try {
      const consent = await firstValueFrom(
        this.service.signConsent(this.data.consent.id, {
          signed_by_name: this.name.trim(),
          signer_id_number: this.idNumber.trim() || null,
          signer_relationship: this.relationship.toLowerCase(),
          signature_image: firma,
          professional_signature_image: this.withProfessional ? (this.professionalPad?.dataUrl() ?? null) : null,
          witness_name: this.witness.trim() || null,
        }),
      );
      this.ref.close(consent);
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.error.set(typeof detail === 'string' ? detail : 'No se pudo guardar la firma.');
    } finally {
      this.saving.set(false);
    }
  }
}

export function openConsentSign(dialog: MatDialog, data: ConsentSignData): Promise<Consent | undefined> {
  return firstValueFrom(
    dialog
      .open<ConsentSignDialogComponent, ConsentSignData, Consent>(ConsentSignDialogComponent, {
        data,
        width: '680px',
        maxWidth: '96vw',
        panelClass: 'app-dialog',
        autoFocus: false,
      })
      .afterClosed(),
  );
}
