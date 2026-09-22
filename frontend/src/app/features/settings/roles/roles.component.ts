import { Component, OnInit, TemplateRef, ViewChild, computed, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { confirmAction } from '../../../shared/confirm-dialog/confirm-dialog.component';
import { UsersService } from '../../../core/services/users.service';
import { Permission, Role } from '../../../core/models/rbac.models';

interface PermissionGroup {
  module: string;
  label: string;
  permissions: Permission[];
}

/** Nombres legibles de cada módulo; lo que no esté aquí se muestra tal cual. */
const MODULE_LABELS: Record<string, string> = {
  appointments: 'Agenda',
  audit: 'Auditoría',
  budgets: 'Presupuestos',
  consents: 'Consentimientos',
  diagnoses: 'Diagnósticos',
  documents: 'Documentos',
  evolutions: 'Evoluciones',
  imaging: 'Imágenes',
  inventory: 'Inventario',
  laboratory: 'Laboratorio',
  medical_history: 'Historia médica',
  odontogram: 'Odontograma',
  patients: 'Pacientes',
  payments: 'Caja y pagos',
  periodontogram: 'Periodontograma',
  prescriptions: 'Recetas',
  reports: 'Reportes',
  roles: 'Roles',
  settings: 'Configuración',
  treatments: 'Tratamientos',
  users: 'Usuarios',
};

@Component({
  selector: 'app-roles',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatCheckboxModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
  ],
  templateUrl: './roles.component.html',
  styleUrl: './roles.component.scss',
})
export class RolesComponent implements OnInit {
  private readonly usersService = inject(UsersService);
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);
  private readonly dialog = inject(MatDialog);

  @ViewChild('formDialog') formDialog!: TemplateRef<unknown>;
  private dialogRef: MatDialogRef<unknown> | null = null;

  readonly roles = signal<Role[]>([]);
  readonly permissionGroups = signal<PermissionGroup[]>([]);
  readonly selectedRole = signal<Role | null>(null);
  readonly selectedCodes = signal<Set<string>>(new Set());
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  /** Rol cuyo nombre se edita; null cuando el diálogo crea uno nuevo. */
  readonly editingRole = signal<Role | null>(null);

  /** Hay cambios sin guardar: los permisos marcados difieren de los del rol. */
  readonly dirty = computed(() => {
    const role = this.selectedRole();
    if (!role) return false;
    const saved = new Set(role.permissions.map((p) => p.code));
    const current = this.selectedCodes();
    return saved.size !== current.size || [...current].some((code) => !saved.has(code));
  });

  readonly newRoleForm = this.fb.nonNullable.group({
    name: ['', Validators.required],
    description: [''],
    copy_from: [''],
  });

  async ngOnInit(): Promise<void> {
    await this.reload();
    if (!this.selectedRole() && this.roles().length > 0) this.selectRole(this.roles()[0]);
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
      Array.from(groups.entries())
        .map(([module, perms]) => ({ module, label: MODULE_LABELS[module] ?? module, permissions: perms }))
        .sort((a, b) => a.label.localeCompare(b.label, 'es')),
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

  groupState(group: PermissionGroup): 'all' | 'some' | 'none' {
    const count = group.permissions.filter((p) => this.selectedCodes().has(p.code)).length;
    if (count === 0) return 'none';
    return count === group.permissions.length ? 'all' : 'some';
  }

  /** Marca o desmarca un módulo entero de una vez. */
  toggleGroup(group: PermissionGroup): void {
    const current = new Set(this.selectedCodes());
    const select = this.groupState(group) !== 'all';
    for (const p of group.permissions) {
      if (select) current.add(p.code);
      else current.delete(p.code);
    }
    this.selectedCodes.set(current);
  }

  discardChanges(): void {
    this.selectRole(this.selectedRole());
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
      this.snackBar.open('No se pudieron guardar los permisos', 'Cerrar', { duration: 4000 });
    } finally {
      this.saving.set(false);
    }
  }

  /** Abre el diálogo; con `base` sale ya preparado como copia de ese rol. */
  openNewRole(base: Role | null = null): void {
    this.editingRole.set(null);
    this.error.set(null);
    this.newRoleForm.reset({
      name: base ? `${base.name} (copia)` : '',
      description: '',
      copy_from: base?.id ?? '',
    });
    this.dialogRef = this.dialog.open(this.formDialog, {
      width: '520px',
      maxWidth: '96vw',
      autoFocus: 'first-tabbable',
      panelClass: 'app-dialog',
    });
  }

  openEditRole(role: Role): void {
    this.editingRole.set(role);
    this.error.set(null);
    this.newRoleForm.reset({ name: role.name, description: role.description ?? '', copy_from: '' });
    this.dialogRef = this.dialog.open(this.formDialog, {
      width: '520px',
      maxWidth: '96vw',
      autoFocus: 'first-tabbable',
      panelClass: 'app-dialog',
    });
  }

  async deleteRole(role: Role): Promise<void> {
    const ok = await confirmAction(this.dialog, {
      title: `¿Eliminar el rol "${role.name}"?`,
      message: 'Solo se puede si ningún usuario lo tiene asignado.',
      confirmLabel: 'Eliminar',
      danger: true,
    });
    if (!ok) return;
    try {
      await firstValueFrom(this.usersService.deleteRole(role.id));
      this.snackBar.open('Rol eliminado', 'Cerrar', { duration: 3000 });
      this.selectRole(null);
      await this.reload();
      if (this.roles().length > 0) this.selectRole(this.roles()[0]);
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.snackBar.open(typeof detail === 'string' ? detail : 'No se pudo eliminar el rol', 'Cerrar', {
        duration: 4500,
      });
    }
  }

  async createRole(): Promise<void> {
    const editing = this.editingRole();
    if (editing) {
      await this.saveRoleDetails(editing);
      return;
    }
    if (this.newRoleForm.invalid) {
      this.newRoleForm.markAllAsTouched();
      return;
    }
    if (this.saving()) return;
    this.saving.set(true);
    this.error.set(null);
    try {
      const { name, description, copy_from } = this.newRoleForm.getRawValue();
      const source = this.roles().find((r) => r.id === copy_from);
      const created = await firstValueFrom(
        this.usersService.createRole({
          name: name.trim(),
          description: description.trim() || null,
          permission_codes: source?.permissions.map((p) => p.code) ?? [],
        }),
      );
      this.dialogRef?.close();
      this.snackBar.open('Rol creado: ajuste sus permisos y guarde', 'Cerrar', { duration: 3500 });
      await this.reload();
      this.selectRole(this.roles().find((r) => r.id === created.id) ?? null);
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.error.set(typeof detail === 'string' ? detail : 'No se pudo crear el rol.');
    } finally {
      this.saving.set(false);
    }
  }

  private async saveRoleDetails(role: Role): Promise<void> {
    if (this.newRoleForm.invalid) {
      this.newRoleForm.markAllAsTouched();
      return;
    }
    if (this.saving()) return;
    this.saving.set(true);
    this.error.set(null);
    try {
      const { name, description } = this.newRoleForm.getRawValue();
      await firstValueFrom(
        this.usersService.updateRole(role.id, { name: name.trim(), description: description.trim() || null }),
      );
      this.dialogRef?.close();
      this.snackBar.open('Rol actualizado', 'Cerrar', { duration: 3000 });
      await this.reload();
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.error.set(typeof detail === 'string' ? detail : 'No se pudo guardar el rol.');
    } finally {
      this.saving.set(false);
    }
  }
}
