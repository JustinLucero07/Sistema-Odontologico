import { Component, OnInit, TemplateRef, ViewChild, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { UsersService } from '../../../core/services/users.service';
import { Role, User } from '../../../core/models/rbac.models';
import { confirmAction } from '../../../shared/confirm-dialog/confirm-dialog.component';
import { promptText } from '../../../shared/confirm-dialog/prompt-dialog.component';

@Component({
  selector: 'app-users',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatTooltipModule,
    MatSelectModule,
    MatTableModule,
  ],
  templateUrl: './users.component.html',
  styleUrl: './users.component.scss',
})
export class UsersComponent implements OnInit {
  private readonly usersService = inject(UsersService);
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);
  private readonly dialog = inject(MatDialog);
  readonly auth = inject(AuthService);

  @ViewChild('formDialog') formDialog!: TemplateRef<unknown>;
  private dialogRef: MatDialogRef<unknown> | null = null;
  readonly error = signal<string | null>(null);
  readonly showPassword = signal(false);

  readonly users = signal<User[]>([]);
  readonly roles = signal<Role[]>([]);
  readonly saving = signal(false);
  /** El usuario que se edita, o null cuando el diálogo crea uno nuevo. */
  readonly editing = signal<User | null>(null);
  readonly displayedColumns = ['name', 'email', 'roles', 'status', 'actions'];

  readonly form = this.fb.nonNullable.group({
    first_name: ['', Validators.required],
    last_name: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    role_ids: this.fb.nonNullable.control<string[]>([]),
  });

  async ngOnInit(): Promise<void> {
    await this.reload();
  }

  async reload(): Promise<void> {
    const [users, roles] = await Promise.all([
      firstValueFrom(this.usersService.listUsers()),
      firstValueFrom(this.usersService.listRoles()),
    ]);
    this.users.set(users);
    this.roles.set(roles);
  }

  open(user: User | null = null): void {
    this.editing.set(user);
    this.form.reset({
      first_name: user?.first_name ?? '',
      last_name: user?.last_name ?? '',
      email: user?.email ?? '',
      password: '',
      role_ids: user?.roles.map((r) => r.id) ?? [],
    });
    // Al editar, el correo es el usuario de acceso y no cambia; la contraseña
    // tiene su propia acción. Se desactivan para que no bloqueen el guardado.
    if (user) {
      this.form.controls.email.disable();
      this.form.controls.password.disable();
    } else {
      this.form.controls.email.enable();
      this.form.controls.password.enable();
    }
    this.error.set(null);
    this.showPassword.set(false);
    this.dialogRef = this.dialog.open(this.formDialog, {
      width: '600px',
      maxWidth: '96vw',
      autoFocus: 'first-tabbable',
      panelClass: 'app-dialog',
    });
  }

  async submit(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    if (this.saving()) return;
    this.saving.set(true);
    this.error.set(null);
    try {
      const value = this.form.getRawValue();
      const editing = this.editing();
      if (editing) {
        await firstValueFrom(
          this.usersService.updateUser(editing.id, {
            first_name: value.first_name,
            last_name: value.last_name,
            role_ids: value.role_ids,
          }),
        );
        this.snackBar.open('Usuario actualizado', 'Cerrar', { duration: 3000 });
      } else {
        await firstValueFrom(this.usersService.createUser(value));
        this.snackBar.open('Usuario creado. Entregue la contraseña temporal en persona.', 'Cerrar', {
          duration: 4000,
        });
      }
      this.dialogRef?.close();
      await this.reload();
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.error.set(typeof detail === 'string' ? detail : 'No se pudo guardar el usuario.');
    } finally {
      this.saving.set(false);
    }
  }

  async deactivate(user: User): Promise<void> {
    const ok = await confirmAction(this.dialog, {
      title: `¿Desactivar a ${user.first_name} ${user.last_name}?`,
      message: 'No podrá volver a iniciar sesión. Su historial y lo que registró se conservan.',
      confirmLabel: 'Desactivar',
      danger: true,
    });
    if (!ok) return;
    await firstValueFrom(this.usersService.deactivateUser(user.id));
    this.snackBar.open('Usuario desactivado', 'Cerrar', { duration: 3000 });
    await this.reload();
  }

  async reactivate(user: User): Promise<void> {
    await firstValueFrom(this.usersService.updateUser(user.id, { is_active: true }));
    this.snackBar.open('Usuario reactivado: ya puede volver a entrar', 'Cerrar', { duration: 3000 });
    await this.reload();
  }

  async resetPassword(user: User): Promise<void> {
    const password = await promptText(this.dialog, {
      title: `Nueva contraseña para ${user.first_name}`,
      message:
        'Se cerrarán todas sus sesiones abiertas (web y app). Entréguele la contraseña en persona y pídale que la cambie.',
      label: 'Contraseña temporal',
      minLength: 8,
      confirmLabel: 'Restablecer',
    });
    if (!password) return;
    try {
      await firstValueFrom(this.usersService.updateUser(user.id, { password }));
      this.snackBar.open('Contraseña restablecida y sesiones cerradas', 'Cerrar', { duration: 3500 });
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.snackBar.open(typeof detail === 'string' ? detail : 'No se pudo cambiar la contraseña', 'Cerrar', {
        duration: 4000,
      });
    }
  }

  initials(user: User): string {
    return `${user.first_name.charAt(0)}${user.last_name.charAt(0)}`.toUpperCase();
  }
}
