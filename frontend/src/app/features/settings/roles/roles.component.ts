import { Component, OnInit, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { UsersService } from '../../../core/services/users.service';
import { Permission, Role } from '../../../core/models/rbac.models';

interface PermissionGroup {
  module: string;
  permissions: Permission[];
}

@Component({
  selector: 'app-roles',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
  ],
  templateUrl: './roles.component.html',
  styleUrl: './roles.component.scss',
})
export class RolesComponent implements OnInit {
  private readonly usersService = inject(UsersService);
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);

  readonly roles = signal<Role[]>([]);
  readonly permissionGroups = signal<PermissionGroup[]>([]);
  readonly selectedRole = signal<Role | null>(null);
  readonly selectedCodes = signal<Set<string>>(new Set());
  readonly saving = signal(false);

  readonly newRoleForm = this.fb.nonNullable.group({
    name: ['', Validators.required],
    description: [''],
  });

  async ngOnInit(): Promise<void> {
    await this.reload();
  }

  async reload(): Promise<void> {
    const [roles, permissions] = await Promise.all([
      firstValueFrom(this.usersService.listRoles()),
      firstValueFrom(this.usersService.listPermissions()),
    ]);
    this.roles.set(roles);

    const groups = new Map<string, Permission[]>();
    for (const permission of permissions) {
      const list = groups.get(permission.module) ?? [];
      list.push(permission);
      groups.set(permission.module, list);
    }
    this.permissionGroups.set(
      Array.from(groups.entries()).map(([module, perms]) => ({ module, permissions: perms })),
    );

    if (this.selectedRole()) {
      const refreshed = roles.find((r) => r.id === this.selectedRole()!.id) ?? null;
      this.selectRole(refreshed);
    }
  }

  selectRole(role: Role | null): void {
    this.selectedRole.set(role);
    this.selectedCodes.set(new Set(role?.permissions.map((p) => p.code) ?? []));
  }

  togglePermission(code: string): void {
    const current = new Set(this.selectedCodes());
    if (current.has(code)) {
      current.delete(code);
    } else {
      current.add(code);
    }
    this.selectedCodes.set(current);
  }

  async savePermissions(): Promise<void> {
    const role = this.selectedRole();
    if (!role || this.saving()) return;

    this.saving.set(true);
    try {
      await firstValueFrom(
        this.usersService.updateRole(role.id, { permission_codes: Array.from(this.selectedCodes()) }),
      );
      this.snackBar.open('Permisos actualizados', 'Cerrar', { duration: 3000 });
      await this.reload();
    } catch {
      this.snackBar.open(
        'No se pudo actualizar: los roles base son de solo lectura, duplique el rol para personalizarlo',
        'Cerrar',
        { duration: 4000 },
      );
    } finally {
      this.saving.set(false);
    }
  }

  async createRole(): Promise<void> {
    if (this.newRoleForm.invalid || this.saving()) return;
    this.saving.set(true);
    try {
      const { name, description } = this.newRoleForm.getRawValue();
      await firstValueFrom(this.usersService.createRole({ name, description, permission_codes: [] }));
      this.newRoleForm.reset();
      this.snackBar.open('Rol creado', 'Cerrar', { duration: 3000 });
      await this.reload();
    } finally {
      this.saving.set(false);
    }
  }
}
