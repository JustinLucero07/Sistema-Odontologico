import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { firstValueFrom } from 'rxjs';

import { Patient, Sex } from '../../core/models/patient.models';
import { PatientsService } from '../../core/services/patients.service';
import { CONSENT_METHOD_LABELS, ConsentMethod, LegalService } from '../../core/services/legal.service';
import { printPrivacyNotice } from '../print/privacy-print';

/**
 * Alta de paciente en un diálogo.
 *
 * Antes era un formulario que se desplegaba encima de la lista y empujaba la
 * tabla hacia abajo. En un diálogo el contexto no se mueve, el foco va directo
 * al primer campo, y Escape cancela sin perder la búsqueda que había.
 *
 * Solo nombre y apellido son obligatorios: en recepción, con el paciente
 * delante, lo urgente es poder agendarlo; el resto se completa en la ficha.
 */
@Component({
  selector: 'app-patient-create-dialog',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule,
  ],
  template: `
    <div class="dialog-head">
      <span class="dialog-icon"><mat-icon>person_add</mat-icon></span>
      <div>
        <h2>Nuevo paciente</h2>
        <p>Solo nombre y apellidos son obligatorios. El resto puede completarse en la ficha.</p>
      </div>
    </div>

    <form [formGroup]="form" (ngSubmit)="save()">
      <mat-dialog-content>
        <h3 class="group-title">Datos personales</h3>
        <div class="grid">
          <mat-form-field appearance="outline">
            <mat-label>Nombres</mat-label>
            <input matInput formControlName="first_name" cdkFocusInitial autocomplete="off" />
            @if (form.controls.first_name.hasError('required')) {
              <mat-error>Escriba el nombre</mat-error>
            }
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Apellidos</mat-label>
            <input matInput formControlName="last_name" autocomplete="off" />
            @if (form.controls.last_name.hasError('required')) {
              <mat-error>Escriba los apellidos</mat-error>
            }
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Cédula</mat-label>
            <input matInput formControlName="national_id" autocomplete="off" />
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Fecha de nacimiento</mat-label>
            <input matInput type="date" formControlName="birth_date" [max]="today" />
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Sexo</mat-label>
            <mat-select formControlName="sex">
              <mat-option value="">Sin especificar</mat-option>
              <mat-option value="F">Femenino</mat-option>
              <mat-option value="M">Masculino</mat-option>
              <mat-option value="O">Otro</mat-option>
            </mat-select>
          </mat-form-field>
        </div>

        <h3 class="group-title">Contacto</h3>
        <div class="grid">
          <mat-form-field appearance="outline">
            <mat-label>Teléfono</mat-label>
            <mat-icon matPrefix>call</mat-icon>
            <input matInput type="tel" formControlName="phone" autocomplete="off" />
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>WhatsApp</mat-label>
            <mat-icon matPrefix>chat</mat-icon>
            <input matInput type="tel" formControlName="whatsapp" autocomplete="off" />
            <mat-hint>
              <button type="button" class="link-btn" (click)="copyPhone()"
                      [disabled]="!form.controls.phone.value">
                Usar el mismo que el teléfono
              </button>
            </mat-hint>
          </mat-form-field>

          <mat-form-field appearance="outline" class="span-2">
            <mat-label>Correo electrónico</mat-label>
            <mat-icon matPrefix>mail</mat-icon>
            <input matInput type="email" formControlName="email" autocomplete="off" />
            @if (form.controls.email.hasError('email')) {
              <mat-error>El correo no tiene un formato válido</mat-error>
            }
          </mat-form-field>
        </div>

        <h3 class="group-title">Protección de datos</h3>
        <div class="privacy" [class.missing]="form.controls.notice_given.touched && form.controls.notice_given.invalid">
          <mat-checkbox formControlName="notice_given">
            Informé al paciente cómo se tratan sus datos y le entregué el aviso de privacidad
          </mat-checkbox>
          <div class="privacy-row">
            <mat-form-field appearance="outline" subscriptSizing="dynamic">
              <mat-label>Cómo se informó</mat-label>
              <mat-select formControlName="notice_method">
                @for (m of methods; track m.value) {
                  <mat-option [value]="m.value">{{ m.label }}</mat-option>
                }
              </mat-select>
            </mat-form-field>
            <button mat-button type="button" (click)="printNotice()">
              <mat-icon>print</mat-icon>
              Imprimir aviso para firmar
            </button>
          </div>
          <mat-checkbox formControlName="communications">
            Autoriza recibir recordatorios y mensajes por WhatsApp o correo
            <span class="optional">(opcional, puede retirarlo cuando quiera)</span>
          </mat-checkbox>
          @if (isMinor()) {
            <mat-form-field appearance="outline" class="rep" subscriptSizing="dynamic">
              <mat-label>Representante legal (paciente menor de edad)</mat-label>
              <input matInput formControlName="representative" placeholder="Nombre y parentesco" />
            </mat-form-field>
          }
          @if (form.controls.notice_given.touched && form.controls.notice_given.invalid) {
            <p class="privacy-error">La ley exige informar al paciente antes de registrar sus datos.</p>
          }
          @if (isMinor() && form.controls.representative.touched && !form.controls.representative.value.trim()) {
            <p class="privacy-error">Indique quién representa al menor.</p>
          }
        </div>

        @if (error()) {
          <p class="form-error"><mat-icon>error_outline</mat-icon>{{ error() }}</p>
        }
      </mat-dialog-content>

      <mat-dialog-actions align="end">
        <button mat-button type="button" mat-dialog-close>Cancelar</button>
        <button mat-flat-button type="submit" [disabled]="saving()">
          {{ saving() ? 'Guardando…' : 'Crear y abrir ficha' }}
        </button>
      </mat-dialog-actions>
    </form>
  `,
  styles: [
    `
      :host { display: block; }
      .dialog-head {
        display: flex; gap: 14px; align-items: flex-start;
        padding: 22px 24px 4px;
        h2 { margin: 0; font-size: 1.15rem; }
        p { margin: 2px 0 0; font-size: 0.8rem; color: var(--color-ink-faint); }
      }
      .dialog-icon {
        display: inline-flex; align-items: center; justify-content: center;
        width: 42px; height: 42px; flex-shrink: 0; border-radius: 12px;
        background: var(--color-primary-soft); color: var(--color-primary);
      }
      .group-title {
        margin: 10px 0 8px; font-size: 0.72rem; font-weight: 700;
        letter-spacing: 0.06em; text-transform: uppercase; color: var(--color-ink-faint);
      }
      .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 14px; }
      .span-2 { grid-column: span 2; }
      .link-btn {
        border: none; background: none; padding: 0; cursor: pointer;
        font: inherit; color: var(--color-primary);
        &:disabled { color: var(--color-ink-faint); cursor: default; }
      }
      .form-error {
        display: flex; align-items: center; gap: 8px; margin: 4px 0 0;
        padding: 10px 12px; border-radius: var(--radius-sm);
        background: var(--color-danger-soft); color: var(--color-danger); font-size: 0.84rem;
        mat-icon { font-size: 18px; width: 18px; height: 18px; }
      }
      mat-dialog-actions { padding: 8px 24px 20px; }
      .privacy {
        display: grid; gap: 8px; padding: 12px 14px; border-radius: var(--radius-md);
        background: var(--color-surface-muted); border: 1px solid var(--color-border);
        &.missing { border-color: var(--color-danger); }
      }
      .privacy-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding-left: 40px; }
      .privacy-row mat-form-field { width: 240px; }
      .rep { padding-left: 40px; width: 100%; }
      .optional { color: var(--color-ink-faint); font-size: 0.8rem; }
      .privacy-error { margin: 0; padding-left: 40px; font-size: 0.78rem; color: var(--color-danger); }
      @media (max-width: 600px) {
        .grid { grid-template-columns: 1fr; }
        .span-2 { grid-column: auto; }
      }
    `,
  ],
})
export class PatientCreateDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly patients = inject(PatientsService);
  private readonly legal = inject(LegalService);
  private readonly ref = inject(MatDialogRef<PatientCreateDialogComponent, Patient>);

  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly today = new Date().toISOString().slice(0, 10);

  readonly form = this.fb.nonNullable.group({
    first_name: ['', Validators.required],
    last_name: ['', Validators.required],
    national_id: [''],
    birth_date: [''],
    sex: [''],
    phone: [''],
    whatsapp: [''],
    email: ['', Validators.email],
    notice_given: [false, Validators.requiredTrue],
    notice_method: ['firma_presencial' as ConsentMethod],
    communications: [false],
    representative: [''],
  });

  readonly methods = Object.entries(CONSENT_METHOD_LABELS).map(([value, label]) => ({
    value: value as ConsentMethod,
    label,
  }));

  /** Menor de edad según la fecha escrita: su representante firma por él. */
  isMinor(): boolean {
    const raw = this.form.controls.birth_date.value;
    if (!raw) return false;
    const birth = new Date(`${raw}T00:00:00`);
    const now = new Date();
    let age = now.getFullYear() - birth.getFullYear();
    if (now.getMonth() < birth.getMonth() || (now.getMonth() === birth.getMonth() && now.getDate() < birth.getDate())) {
      age -= 1;
    }
    return age < 18;
  }

  async printNotice(): Promise<void> {
    const controller = await firstValueFrom(this.legal.getController());
    const v = this.form.getRawValue();
    const name = `${v.first_name} ${v.last_name}`.trim();
    printPrivacyNotice(controller, name || null);
  }

  copyPhone(): void {
    this.form.controls.whatsapp.setValue(this.form.controls.phone.value);
  }

  async save(): Promise<void> {
    const missingRepresentative = this.isMinor() && !this.form.controls.representative.value.trim();
    if (this.form.invalid || missingRepresentative) {
      // Marcar todo como tocado para que los mensajes aparezcan en los campos,
      // en lugar de un botón gris que no explica por qué no hace nada.
      this.form.markAllAsTouched();
      return;
    }
    if (this.saving()) return;
    this.saving.set(true);
    this.error.set(null);
    try {
      const v = this.form.getRawValue();
      const trim = (x: string) => x.trim() || null;
      const created = await firstValueFrom(
        this.patients.createPatient({
          first_name: v.first_name.trim(),
          last_name: v.last_name.trim(),
          national_id: trim(v.national_id),
          birth_date: v.birth_date || null,
          sex: (v.sex || null) as Sex | null,
          phone: trim(v.phone),
          whatsapp: trim(v.whatsapp),
          email: trim(v.email),
        }),
      );
      // La constancia de que se informó al paciente se guarda junto con el alta.
      const signedBy = this.isMinor() ? v.representative.trim() : null;
      try {
        await firstValueFrom(
          this.legal.recordConsent(created.id, {
            kind: 'aviso_privacidad',
            method: v.notice_method,
            signed_by_name: signedBy,
          }),
        );
        if (v.communications) {
          await firstValueFrom(
            this.legal.recordConsent(created.id, {
              kind: 'comunicaciones',
              granted: true,
              method: v.notice_method,
              signed_by_name: signedBy,
            }),
          );
        }
      } catch {
        // El paciente ya existe: la constancia puede registrarse desde su ficha,
        // que la muestra como pendiente. No se pierde el alta por esto.
      }
      this.ref.close(created);
    } catch (e) {
      const detail = (e as { error?: { detail?: unknown } })?.error?.detail;
      this.error.set(
        typeof detail === 'string' ? detail : 'No se pudo crear el paciente. Revise los datos.',
      );
    } finally {
      this.saving.set(false);
    }
  }
}

/** Abre el diálogo. Devuelve el paciente creado, o undefined si se canceló. */
export function openPatientCreateDialog(dialog: MatDialog): Promise<Patient | undefined> {
  return firstValueFrom(
    dialog
      .open(PatientCreateDialogComponent, {
        width: '640px',
        maxWidth: '96vw',
        autoFocus: 'first-tabbable',
        panelClass: 'app-dialog',
      })
      .afterClosed(),
  );
}
