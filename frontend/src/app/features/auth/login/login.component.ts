import { HttpErrorResponse } from '@angular/common/http';
import { Component, ElementRef, inject, signal, viewChild } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { ToothMarkComponent } from '../../../shared/brand/tooth-mark.component';
import { BrandingService } from '../../../core/branding/branding.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    ToothMarkComponent,
  ],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  readonly branding = inject(BrandingService);
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly hidePassword = signal(true);

  // Solo el correo se recuerda aquí. La contraseña la guarda el gestor de
  // contraseñas del navegador (cifrado y protegido por el sistema), nunca la app.
  private static readonly CLAVE_CORREO = 'login.correo';
  readonly recordar = signal(true);
  private readonly correo = viewChild<ElementRef<HTMLInputElement>>('correo');
  private readonly clave = viewChild<ElementRef<HTMLInputElement>>('clave');

  readonly form = this.fb.nonNullable.group({
    email: [LoginComponent.leerCorreo(), [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
  });

  private static leerCorreo(): string {
    try { return localStorage.getItem(LoginComponent.CLAVE_CORREO) ?? ''; } catch { return ''; }
  }

  async submit(): Promise<void> {
    // El autollenado del navegador no avisa a Angular hasta que el usuario
    // toca la página: se toman los valores que ya están en los campos.
    const correo = this.correo()?.nativeElement.value ?? '';
    const clave = this.clave()?.nativeElement.value ?? '';
    if (correo && correo !== this.form.controls.email.value) this.form.controls.email.setValue(correo);
    if (clave && clave !== this.form.controls.password.value) this.form.controls.password.setValue(clave);
    this.form.markAllAsTouched();
    if (this.form.invalid || this.loading()) return;

    this.loading.set(true);
    this.errorMessage.set(null);

    try {
      await firstValueFrom(this.auth.login(this.form.getRawValue()));
      await this.guardarCredenciales();
      await this.auth.loadCurrentUser();
      await this.router.navigate(['/dashboard']);
    } catch (error) {
      if (error instanceof HttpErrorResponse && error.status === 401) {
        this.errorMessage.set('Correo o contraseña incorrectos.');
      } else {
        this.errorMessage.set('No se pudo iniciar sesión. Intente nuevamente.');
      }
    } finally {
      this.loading.set(false);
    }
  }

  // Tras un ingreso correcto: recordar el correo (si se pidió) y ofrecer al
  // navegador guardar la contraseña. Chrome y Edge lo hacen con la API de
  // credenciales; Firefox y Safari lo detectan por el propio formulario.
  private async guardarCredenciales(): Promise<void> {
    const { email, password } = this.form.getRawValue();
    try {
      if (this.recordar()) localStorage.setItem(LoginComponent.CLAVE_CORREO, email);
      else localStorage.removeItem(LoginComponent.CLAVE_CORREO);
    } catch { /* almacenamiento bloqueado: no pasa nada */ }
    const PC = (window as unknown as { PasswordCredential?: new (d: { id: string; password: string; name?: string }) => Credential }).PasswordCredential;
    if (PC && navigator.credentials?.store) {
      try { await navigator.credentials.store(new PC({ id: email, password, name: email })); } catch { /* el usuario puede rechazarlo */ }
    }
  }
}
