import { Component, OnInit, ViewChild, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { firstValueFrom } from 'rxjs';

import { PublicConsentView } from '../../core/models/clinical-record.models';
import { ClinicalRecordsService } from '../../core/services/clinical-records.service';
import { RELATIONSHIPS } from '../../shared/consents/consent-sign-dialog.component';
import { SignaturePadComponent } from '../../shared/consents/signature-pad.component';

/** Página pública donde el paciente lee y firma su consentimiento desde el
 *  teléfono. No hay sesión: el enlace es la credencial y sirve una sola vez. */
@Component({
  selector: 'app-consent-sign-page',
  standalone: true,
  imports: [FormsModule, MatButtonModule, MatCheckboxModule, MatFormFieldModule, MatIconModule, MatInputModule, MatSelectModule, SignaturePadComponent],
  template: `
    <main class="wrap">
      @if (loading()) {
        <p class="center">Cargando…</p>
      } @else if (done()) {
        <section class="card center">
          <mat-icon class="big ok">task_alt</mat-icon>
          <h1>¡Gracias, ya está firmado!</h1>
          <p>{{ view()?.clinic_name }} recibió su consentimiento firmado. Ya puede cerrar esta página.</p>
        </section>
      } @else if (error()) {
        <section class="card center">
          <mat-icon class="big bad">link_off</mat-icon>
          <h1>Enlace no disponible</h1>
          <p>{{ error() }}</p>
        </section>
      } @else {
        @if (view(); as v) {
        <header class="brand" [style.background]="v.clinic_color || '#0D7F76'">
          @if (v.clinic_logo) { <img [src]="v.clinic_logo" alt="" /> }
          <span>{{ v.clinic_name }}</span>
        </header>
        <section class="card">
          <p class="over">Consentimiento informado para</p>
          <h1>{{ v.patient_name }}</h1>
          <h2>{{ v.title }}</h2>
          <div class="body">{{ v.body }}</div>
        </section>

        <section class="card">
          <h3>Sus datos</h3>
          <mat-form-field appearance="outline">
            <mat-label>Quién firma</mat-label>
            <mat-select [(ngModel)]="relationship">
              @for (r of relationships; track r) { <mat-option [value]="r">{{ r }}</mat-option> }
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Nombre completo</mat-label>
            <input matInput [(ngModel)]="name" autocomplete="name" />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Cédula</mat-label>
            <input matInput [(ngModel)]="idNumber" inputmode="numeric" />
          </mat-form-field>

          <h3>Firma</h3>
          <app-signature-pad #pad label="Firme con el dedo dentro del recuadro" placeholder="Firme aquí" />

          <mat-checkbox [(ngModel)]="accept" class="accept">He leído el consentimiento completo, entiendo su contenido y lo acepto.</mat-checkbox>

          @if (formError()) { <p class="err">{{ formError() }}</p> }
          <button mat-flat-button class="send" (click)="sign()" [disabled]="sending() || !accept || name.trim().length < 3">
            {{ sending() ? 'Enviando…' : 'Firmar y enviar' }}
          </button>
          <p class="fine">Se registrará la fecha, la hora y la dirección IP de su firma. Este enlace sirve una sola vez.</p>
        </section>
        }
      }
    </main>
  `,
  styles: [
    `
      :host { display: block; min-height: 100vh; background: #f6f4ef; color: #14242b; }
      .wrap { max-width: 720px; margin: 0 auto; padding: 16px 14px 40px; display: grid; gap: 14px; }
      .brand { display: flex; align-items: center; gap: 12px; padding: 14px 18px; border-radius: 18px; color: #fff; font-weight: 700; font-size: 1.05rem;
        img { height: 40px; width: 40px; object-fit: contain; background: #fff; border-radius: 10px; padding: 3px; } }
      .card { background: #fff; border-radius: 20px; padding: 20px 18px; box-shadow: 0 10px 30px -18px rgba(0,0,0,0.25); display: grid; gap: 6px; }
      .over { margin: 0; font-size: 0.78rem; letter-spacing: 0.1em; text-transform: uppercase; color: #6b7a7e; }
      h1 { margin: 0; font-size: 1.5rem; } h2 { margin: 4px 0 10px; font-size: 1.1rem; color: #0d5f58; }
      h3 { margin: 6px 0 4px; font-size: 0.95rem; }
      .body { white-space: pre-line; line-height: 1.6; font-size: 0.98rem; }
      .accept { margin: 10px 0 4px; }
      .send { height: 52px; font-size: 1rem; margin-top: 6px; }
      .fine { margin: 6px 0 0; font-size: 0.78rem; color: #6b7a7e; }
      .err { color: #b3352b; margin: 4px 0; }
      .center { text-align: center; justify-items: center; }
      .big { font-size: 56px; width: 56px; height: 56px; } .ok { color: #2b7a4b; } .bad { color: #b3352b; }
    `,
  ],
})
export class ConsentSignPageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly service = inject(ClinicalRecordsService);

  @ViewChild('pad') pad?: SignaturePadComponent;

  readonly relationships = RELATIONSHIPS;
  readonly view = signal<PublicConsentView | null>(null);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly formError = signal<string | null>(null);
  readonly sending = signal(false);
  readonly done = signal(false);
  private token = '';

  relationship = 'Paciente';
  name = '';
  idNumber = '';
  accept = false;

  async ngOnInit(): Promise<void> {
    this.token = this.route.snapshot.paramMap.get('token') ?? '';
    try {
      const v = await firstValueFrom(this.service.publicConsent(this.token));
      this.view.set(v);
      this.name = v.patient_name;
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.error.set(typeof detail === 'string' ? detail : 'Este enlace ya no es válido. Pida uno nuevo a su consulta.');
    } finally {
      this.loading.set(false);
    }
  }

  async sign(): Promise<void> {
    const firma = this.pad?.dataUrl();
    if (!firma) {
      this.formError.set('Falta su firma: dibújela en el recuadro.');
      return;
    }
    this.formError.set(null);
    this.sending.set(true);
    try {
      await firstValueFrom(
        this.service.publicSign(this.token, {
          signed_by_name: this.name.trim(),
          signer_id_number: this.idNumber.trim() || null,
          signer_relationship: this.relationship.toLowerCase(),
          signature_image: firma,
          accept: this.accept,
        }),
      );
      this.done.set(true);
      window.scrollTo({ top: 0 });
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.formError.set(typeof detail === 'string' ? detail : 'No se pudo enviar la firma. Intente de nuevo.');
    } finally {
      this.sending.set(false);
    }
  }
}
