import { Component, OnInit, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { firstValueFrom } from 'rxjs';

import { UsersService } from '../../../core/services/users.service';
import { Role, User } from '../../../core/models/rbac.models';

@Component({
  selector: 'app-users',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
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

  readonly users = signal<User[]>([]);
  readonly roles = signal<Role[]>([]);
  readonly saving = signal(false);
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

  async submit(): Promise<void> {
    if (this.form.invalid || this.saving()) return;
    this.saving.set(true);
    try {
      await firstValueFrom(this.usersService.createUser(this.form.getRawValue()));
      this.form.reset({ role_ids: [] });
      this.snackBar.open('Usuario creado correctamente', 'Cerrar', { duration: 3000 });
      await this.reload();
    } catch {
      this.snackBar.open('No se pudo crear el usuario', 'Cerrar', { duration: 3000 });
    } finally {
      this.saving.set(false);
    }
  }

  async deactivate(user: User): Promise<void> {
    await firstValueFrom(this.usersService.deactivateUser(user.id));
    await this.reload();
  }
}
