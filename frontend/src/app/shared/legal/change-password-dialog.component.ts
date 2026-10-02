import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';

/** Las mismas reglas que aplica el servidor (core/password_policy.py), para
 *  avisar mientras se escribe. El servidor sigue siendo quien decide. */
function checks(password: string, personal: string[]) {
  const plain = password.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  return [
    { ok: password.length >= 8, label: 'Al menos 8 caracteres' },
    { ok: /[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]/.test(password) && /\d/.test(password), label: 'Letras y números' },
    {
      ok: password.length > 0 && !personal.some((p) => p.length >= 4 && plain.includes(p)),
      label: 'Sin su nombre ni su correo',
    },
  ];
}

/** Fortaleza orientativa de 0 a 4: longitud y variedad de caracteres. */
function strength(password: string): number {
  if (!password) return 0;
  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
  if (/\d/.test(password) && /[^A-Za-z0-9]/.test(password)) score++;
  return Math.max(1, score);
}

@Component({
  selector: 'app-change-password-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatIconModule, MatInputModule],
  template: `
    <div class="head">
      <span class="icon"><mat-icon>key</mat-icon></span>
      <div>
        <h2>{{ data.forced ? 'Cree su contraseña' : 'Cambiar contraseña' }}</h2>
        <p>
          {{
            data.forced
              ? 'Su contraseña actual es temporal: la conoce quien se la entregó. Elija una que solo usted sepa.'
              : 'Al cambiarla se cerrará su sesión en los demás dispositivos.'
          }}
        </p>
      </div>
    </div>
    <form [formGroup]="form" (ngSubmit)="save()">
      <mat-dialog-content>
        <mat-form-field appearance="outline" class="field">
          <mat-label>{{ data.forced ? 'Contraseña temporal' : 'Contraseña actual' }}</mat-label>
          <input matInput [type]="show() ? 'text' : 'password'" formControlName="current" autocomplete="current-password" />
        </mat-form-field>
        <mat-form-field appearance="outline" class="field">
          <mat-label>Nueva contraseña</mat-label>
          <input matInput [type]="show() ? 'text' : 'password'" formControlName="next" autocomplete="new-password" />
          <button mat-icon-button matSuffix type="button" (click)="show.set(!show())"
                  [attr.aria-label]="show() ? 'Ocultar contraseñas' : 'Mostrar contraseñas'">
            <mat-icon>{{ show() ? 'visibility_off' : 'visibility' }}</mat-icon>
          </button>
        </mat-form-field>

        <div class="meter" [attr.data-level]="level()" role="img" [attr.aria-label]="'Fortaleza: ' + levelLabel()">
          <span></span><span></span><span></span><span></span>
          <em>{{ levelLabel() }}</em>
        </div>
        <ul class="rules">
          @for (rule of rules(); track rule.label) {
            <li [class.ok]="rule.ok">
              <mat-icon>{{ rule.ok ? 'check_circle' : 'radio_button_unchecked' }}</mat-icon>{{ rule.label }}
            </li>
          }
        </ul>

        <mat-form-field appearance="outline" class="field">
          <mat-label>Repita la nueva contraseña</mat-label>
          <input matInput [type]="show() ? 'text' : 'password'" formControlName="repeat" autocomplete="new-password" />
          @if (mismatch()) {
            <mat-hint class="bad">No coincide</mat-hint>
          }
        </mat-form-field>
        <p class="tip">Consejo: una frase de varias palabras es más fácil de recordar y más difícil de adivinar.</p>
        @if (error()) {
          <p class="dialog-error">{{ error() }}</p>
        }
      </mat-dialog-content>
      <mat-dialog-actions align="end">
        @if (data.forced) {
          <button mat-button type="button" (click)="logout()">Salir</button>
        } @else {
          <button mat-button type="button" mat-dialog-close>Cancelar</button>
        }
        <button mat-flat-button type="submit" [disabled]="saving() || !valid()">
          {{ saving() ? 'Guardando…' : 'Guardar contraseña' }}
        </button>
      </mat-dialog-actions>
    </form>
  `,
  styles: [
    `
      .head { display: flex; gap: 14px; padding: 22px 24px 4px; }
      .head h2 { margin: 0; font-size: 1.2rem; }
      .head p { margin: 2px 0 0; font-size: 0.84rem; line-height: 1.45; color: var(--color-ink-soft); }
      .icon {
        display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
        width: 44px; height: 44px; border-radius: 14px;
        background: var(--color-primary-soft); color: var(--color-primary);
      }
      .field { width: 100%; margin-top: 6px; }
      .meter {
        display: grid; grid-template-columns: repeat(4, 1fr) auto; align-items: center; gap: 6px; margin: 2px 0 8px;
        span { height: 6px; border-radius: 999px; background: color-mix(in srgb, var(--color-ink) 10%, transparent); transition: background 0.2s ease; }
        em { font-style: normal; font-size: 0.76rem; font-weight: 700; min-width: 70px; text-align: right; color: var(--color-ink-faint); }
        &[data-level='1'] span:nth-child(-n + 1) { background: var(--color-danger); }
        &[data-level='2'] span:nth-child(-n + 2) { background: var(--color-accent); }
        &[data-level='3'] span:nth-child(-n + 3) { background: var(--color-mint); }
        &[data-level='4'] span:nth-child(-n + 4) { background: var(--color-success); }
      }
      .rules {
        list-style: none; margin: 0 0 8px; padding: 0; display: grid; gap: 2px; font-size: 0.8rem; color: var(--color-ink-faint);
        li { display: flex; align-items: center; gap: 6px; }
        li.ok { color: var(--color-success); }
        mat-icon { font-size: 16px; width: 16px; height: 16px; }
      }
      .bad { color: var(--color-danger); }
      .tip { margin: 0; font-size: 0.78rem; color: var(--color-ink-faint); }
    `,
  ],
})
export class ChangePasswordDialogComponent {
  readonly data = inject<{ forced: boolean }>(MAT_DIALOG_DATA);
  private readonly ref = inject(MatDialogRef<ChangePasswordDialogComponent, boolean>);
  private readonly auth = inject(AuthService);

  readonly show = signal(false);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);

  readonly form = inject(FormBuilder).nonNullable.group({
    current: ['', Validators.required],
    next: ['', Validators.required],
    repeat: ['', Validators.required],
  });
  private readonly value = toSignal(this.form.valueChanges, { initialValue: this.form.getRawValue() });

  private readonly personal = (() => {
    const u = this.auth.currentUser();
    const norm = (t: string) => t.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
    return u ? [norm(u.email.split('@')[0]), norm(u.first_name), norm(u.last_name)] : [];
  })();

  readonly rules = computed(() => checks(this.value().next ?? '', this.personal));
  readonly level = computed(() => (this.rules().every((r) => r.ok) ? strength(this.value().next ?? '') : this.value().next ? 1 : 0));
  readonly levelLabel = computed(() => ['', 'Débil', 'Aceptable', 'Buena', 'Fuerte'][this.level()]);
  readonly mismatch = computed(() => !!this.value().repeat && this.value().repeat !== this.value().next);
  readonly valid = computed(
    () => !!this.value().current && this.rules().every((r) => r.ok) && this.value().repeat === this.value().next,
  );

  async save(): Promise<void> {
    if (!this.valid() || this.saving()) return;
    this.saving.set(true);
    this.error.set(null);
    const v = this.form.getRawValue();
    try {
      await firstValueFrom(this.auth.changePassword(v.current, v.next));
      await this.auth.loadCurrentUser();
      this.ref.close(true);
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.error.set(typeof detail === 'string' ? detail : 'No se pudo cambiar la contraseña.');
    } finally {
      this.saving.set(false);
    }
  }

  async logout(): Promise<void> {
    this.ref.close(false);
    await this.auth.logout();
  }
}

export function openChangePassword(dialog: MatDialog, forced = false): Promise<boolean | undefined> {
  return firstValueFrom(
    dialog
      .open(ChangePasswordDialogComponent, {
        data: { forced },
        width: '520px',
        maxWidth: '96vw',
        disableClose: forced,
        panelClass: 'app-dialog',
      })
      .afterClosed(),
  );
}
