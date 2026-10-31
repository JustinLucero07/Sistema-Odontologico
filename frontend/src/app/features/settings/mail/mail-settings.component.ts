import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { MailProvider, MailService, MailSettings } from '../../../core/services/mail.service';
import { confirmAction } from '../../../shared/confirm-dialog/confirm-dialog.component';

@Component({
  selector: 'app-mail-settings',
  standalone: true,
  imports: [DatePipe, FormsModule, MatButtonModule, MatFormFieldModule, MatIconModule, MatInputModule, MatSelectModule, MatSlideToggleModule],
  template: `
    <div class="page">
      <header class="page-header">
        <div>
          <h1>Correo saliente</h1>
          <p class="page-sub">El buzón desde el que salen las facturas, los recordatorios de citas y los consentimientos para firmar</p>
        </div>
      </header>

      @if (s(); as st) {
        <div class="glass-card status" [class.ok]="st.configured && st.last_test_ok !== false" [class.bad]="!st.configured || st.last_test_ok === false">
          <mat-icon>{{ st.configured ? (st.last_test_ok === false ? 'error' : 'mark_email_read') : 'mail_lock' }}</mat-icon>
          <div>
            @if (!st.configured) {
              <strong>Sin correo configurado.</strong>
              <span>Las facturas se envían por WhatsApp o se descargan, y los recordatorios salen solo por WhatsApp.</span>
            } @else if (st.source === 'servidor') {
              <strong>Usando el correo general del servidor.</strong>
              <span>Configure el de su consulta para que los pacientes reciban los correos a su nombre.</span>
            } @else if (st.last_test_ok === false) {
              <strong>La última prueba falló.</strong>
              <span>{{ st.last_error }}</span>
            } @else if (st.last_test_ok) {
              <strong>Funcionando.</strong>
              <span>Última prueba correcta el {{ st.last_test_at | date: 'dd/MM/yyyy HH:mm' }}.</span>
            } @else {
              <strong>Configurado.</strong>
              <span>Envíese un correo de prueba para confirmar que funciona.</span>
            }
          </div>
        </div>

        <section class="grid">
          <article class="glass-card block">
            <h2><mat-icon>dns</mat-icon>Servidor</h2>
            <div class="providers">
              @for (p of providers(); track p.code) {
                <button type="button" [class.on]="provider() === p.code" (click)="pick(p)">{{ p.label }}</button>
              }
            </div>
            @if (help()) { <p class="help"><mat-icon>info</mat-icon>{{ help() }}</p> }
            <div class="row">
              <mat-form-field appearance="outline" class="grow">
                <mat-label>Servidor SMTP</mat-label>
                <input matInput [(ngModel)]="host" placeholder="smtp.gmail.com" />
              </mat-form-field>
              <mat-form-field appearance="outline" class="port">
                <mat-label>Puerto</mat-label>
                <input matInput type="number" [(ngModel)]="port" />
              </mat-form-field>
              <mat-form-field appearance="outline" class="sec">
                <mat-label>Seguridad</mat-label>
                <mat-select [(ngModel)]="security">
                  <mat-option value="starttls">STARTTLS (587)</mat-option>
                  <mat-option value="ssl">SSL/TLS (465)</mat-option>
                  <mat-option value="none">Ninguna</mat-option>
                </mat-select>
              </mat-form-field>
            </div>
            <div class="row">
              <mat-form-field appearance="outline" class="grow">
                <mat-label>Usuario</mat-label>
                <input matInput [(ngModel)]="username" autocomplete="off" placeholder="consultorio@gmail.com" />
              </mat-form-field>
              <mat-form-field appearance="outline" class="grow">
                <mat-label>{{ st.has_password ? 'Contraseña (guardada; escriba para cambiarla)' : 'Contraseña de aplicación' }}</mat-label>
                <input matInput type="password" [(ngModel)]="password" autocomplete="new-password" />
              </mat-form-field>
            </div>
          </article>

          <article class="glass-card block">
            <h2><mat-icon>alternate_email</mat-icon>Remitente</h2>
            <mat-form-field appearance="outline">
              <mat-label>Correo del remitente</mat-label>
              <input matInput type="email" [(ngModel)]="fromEmail" placeholder="El mismo de la cuenta" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Nombre que verá el paciente</mat-label>
              <input matInput [(ngModel)]="fromName" placeholder="Clínica Dental Sonrisa" />
            </mat-form-field>
            <mat-slide-toggle [(ngModel)]="reminders">Enviar también por correo los recordatorios de citas (24 h y 2 h antes)</mat-slide-toggle>
          </article>
        </section>

        <div class="actions">
          @if (st.source === 'consulta') {
            <button mat-button class="danger-text" (click)="clear()">Quitar configuración</button>
          }
          <span class="spacer"></span>
          <button mat-flat-button (click)="save()" [disabled]="busy()"><mat-icon>save</mat-icon>Guardar</button>
        </div>

        <article class="glass-card block test">
          <h2><mat-icon>send</mat-icon>Probar</h2>
          <div class="row">
            <mat-form-field appearance="outline" class="grow" subscriptSizing="dynamic">
              <mat-label>Enviar un correo de prueba a</mat-label>
              <input matInput type="email" [(ngModel)]="testTo" />
            </mat-form-field>
            <button mat-stroked-button (click)="test()" [disabled]="busy() || !st.configured || !testTo">
              {{ busy() ? 'Enviando…' : 'Enviar prueba' }}
            </button>
          </div>
        </article>
      }
    </div>
  `,
  styles: [
    `
      .page { display: grid; gap: 16px; }
      .status { display: flex; gap: 12px; align-items: flex-start; padding: 16px 18px;
        div { display: grid; gap: 2px; } span { color: var(--color-ink-soft); font-size: 0.9rem; }
        &.ok mat-icon { color: var(--color-success); } &.bad mat-icon { color: var(--color-danger); } }
      .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; }
      .block { display: grid; gap: 8px; align-content: start; padding: 18px 20px;
        h2 { display: flex; gap: 8px; align-items: center; margin: 0 0 4px; font-size: 1.02rem; mat-icon { color: var(--color-primary); } } }
      .providers { display: flex; flex-wrap: wrap; gap: 6px;
        button { border: 1px solid var(--color-border); background: var(--glass-field-bg); color: inherit; font: inherit; font-size: 0.85rem; padding: 6px 12px; border-radius: 999px; cursor: pointer; }
        button.on { background: var(--color-primary); color: #fff; border-color: transparent; } }
      .help { display: flex; gap: 8px; align-items: flex-start; margin: 4px 0; padding: 10px 12px; border-radius: 12px; font-size: 0.86rem;
        background: color-mix(in srgb, var(--color-primary) 8%, transparent); mat-icon { color: var(--color-primary); flex: none; } }
      .row { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
      .grow { flex: 1; min-width: 200px; } .port { width: 110px; } .sec { width: 180px; }
      .actions { display: flex; gap: 8px; align-items: center; } .spacer { flex: 1; }
      .danger-text { color: var(--color-danger); }
    `,
  ],
})
export class MailSettingsComponent implements OnInit {
  private readonly service = inject(MailService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly dialog = inject(MatDialog);
  private readonly auth = inject(AuthService);

  readonly s = signal<MailSettings | null>(null);
  readonly providers = signal<MailProvider[]>([]);
  readonly provider = signal<string | null>(null);
  readonly help = signal<string | null>(null);
  readonly busy = signal(false);

  host = '';
  port = 587;
  security: MailSettings['security'] = 'starttls';
  username = '';
  password = '';
  fromEmail = '';
  fromName = '';
  reminders = true;
  testTo = '';

  async ngOnInit(): Promise<void> {
    const [s, providers] = await Promise.all([firstValueFrom(this.service.settings()), firstValueFrom(this.service.providers())]);
    this.providers.set(providers);
    this.apply(s);
    this.testTo = this.auth.currentUser()?.email ?? '';
    this.provider.set(providers.find((p) => p.host && p.host === s.host)?.code ?? (s.host ? 'otro' : null));
    this.help.set(providers.find((p) => p.code === this.provider())?.help ?? null);
  }

  private apply(s: MailSettings): void {
    this.s.set(s);
    this.host = s.host ?? '';
    this.port = s.port;
    this.security = s.security;
    this.username = s.username ?? '';
    this.fromEmail = s.from_email ?? '';
    this.fromName = s.from_name ?? '';
    this.reminders = s.reminders_enabled;
    this.password = '';
  }

  pick(p: MailProvider): void {
    this.provider.set(p.code);
    this.help.set(p.help);
    if (p.host) this.host = p.host;
    this.port = p.port;
    this.security = p.security;
  }

  private report(err: unknown, fallback: string): void {
    const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
    this.snackBar.open(
      typeof detail === 'string' ? detail : Array.isArray(detail) && detail[0]?.msg ? String(detail[0].msg) : fallback,
      'Cerrar',
      { duration: 7000 },
    );
  }

  async save(): Promise<void> {
    this.busy.set(true);
    try {
      this.apply(
        await firstValueFrom(
          this.service.save({
            host: this.host.trim() || null,
            port: this.port,
            security: this.security,
            username: this.username.trim() || null,
            password: this.password || null,
            from_email: this.fromEmail.trim() || this.username.trim() || null,
            from_name: this.fromName.trim() || null,
            reminders_enabled: this.reminders,
          }),
        ),
      );
      this.snackBar.open('Correo guardado. Envíese una prueba.', 'Cerrar', { duration: 3500 });
    } catch (err) {
      this.report(err, 'No se pudo guardar.');
    } finally {
      this.busy.set(false);
    }
  }

  async test(): Promise<void> {
    this.busy.set(true);
    try {
      const s = await firstValueFrom(this.service.test(this.testTo.trim()));
      this.s.set(s);
      this.snackBar.open(s.last_test_ok ? `Correo de prueba enviado a ${this.testTo}` : s.last_error ?? 'Falló', 'Cerrar', { duration: 7000 });
    } catch (err) {
      this.report(err, 'No se pudo enviar la prueba.');
    } finally {
      this.busy.set(false);
    }
  }

  async clear(): Promise<void> {
    if (!(await confirmAction(this.dialog, { title: '¿Quitar el correo de la consulta?', message: 'Dejarán de salir correos con su nombre.', confirmLabel: 'Quitar', danger: true }))) return;
    this.apply(await firstValueFrom(this.service.clear()));
    this.provider.set(null);
    this.help.set(null);
  }
}
