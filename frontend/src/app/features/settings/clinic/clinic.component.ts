import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatMenuModule } from '@angular/material/menu';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { firstValueFrom } from 'rxjs';

import { Branch, Operatory } from '../../../core/models/clinic.models';
import { ClinicService } from '../../../core/services/clinic.service';
import { confirmAction } from '../../../shared/confirm-dialog/confirm-dialog.component';
import { promptText } from '../../../shared/confirm-dialog/prompt-dialog.component';

/** Las zonas de la región; los reportes cuentan los días en la elegida. */
const TIMEZONES = [
  { value: 'America/Guayaquil', label: 'Ecuador (continental)' },
  { value: 'Pacific/Galapagos', label: 'Ecuador (Galápagos)' },
  { value: 'America/Bogota', label: 'Colombia' },
  { value: 'America/Lima', label: 'Perú' },
  { value: 'America/Caracas', label: 'Venezuela' },
  { value: 'America/La_Paz', label: 'Bolivia' },
  { value: 'America/Santiago', label: 'Chile' },
  { value: 'America/Argentina/Buenos_Aires', label: 'Argentina' },
  { value: 'America/Mexico_City', label: 'México (centro)' },
  { value: 'America/Panama', label: 'Panamá' },
  { value: 'America/New_York', label: 'EE. UU. (este)' },
  { value: 'Europe/Madrid', label: 'España' },
];

const CURRENCIES = [
  { value: 'USD', label: 'Dólar estadounidense (USD)' },
  { value: 'COP', label: 'Peso colombiano (COP)' },
  { value: 'PEN', label: 'Sol peruano (PEN)' },
  { value: 'MXN', label: 'Peso mexicano (MXN)' },
  { value: 'CLP', label: 'Peso chileno (CLP)' },
  { value: 'ARS', label: 'Peso argentino (ARS)' },
  { value: 'BOB', label: 'Boliviano (BOB)' },
  { value: 'EUR', label: 'Euro (EUR)' },
];

function errorDetail(err: unknown, fallback: string): string {
  const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && typeof detail[0]?.msg === 'string') return detail[0].msg;
  return fallback;
}

@Component({
  selector: 'app-clinic',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatSelectModule,
    MatTooltipModule,
  ],
  templateUrl: './clinic.component.html',
  styleUrl: './clinic.component.scss',
})
export class ClinicComponent implements OnInit {
  private readonly clinicService = inject(ClinicService);
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);
  private readonly dialog = inject(MatDialog);

  readonly saving = signal(false);
  readonly timezones = signal(TIMEZONES);
  readonly currencies = CURRENCIES;

  readonly branches = signal<Branch[]>([]);
  readonly operatories = signal<Operatory[]>([]);

  readonly roomsByBranch = computed(() => {
    const map = new Map<string, Operatory[]>();
    for (const room of this.operatories()) {
      const list = map.get(room.branch_id) ?? [];
      list.push(room);
      map.set(room.branch_id, list);
    }
    return map;
  });

  readonly form = this.fb.nonNullable.group({
    name: ['', Validators.required],
    legal_name: [''],
    tax_id: [''],
    address: [''],
    phone: [''],
    email: ['', Validators.email],
    timezone: ['America/Guayaquil'],
    currency: ['USD'],
  });

  async ngOnInit(): Promise<void> {
    const clinic = await firstValueFrom(this.clinicService.getMyClinic());
    // Si la clínica ya tenía una zona fuera de la lista, se conserva visible.
    if (!TIMEZONES.some((t) => t.value === clinic.timezone)) {
      this.timezones.set([{ value: clinic.timezone, label: clinic.timezone }, ...TIMEZONES]);
    }
    this.form.patchValue({
      name: clinic.name,
      legal_name: clinic.legal_name ?? '',
      tax_id: clinic.tax_id ?? '',
      address: clinic.address ?? '',
      phone: clinic.phone ?? '',
      email: clinic.email ?? '',
      timezone: clinic.timezone,
      currency: clinic.currency,
    });
    this.form.markAsPristine();
    await this.reloadRooms();
  }

  async submit(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    if (this.saving()) return;
    this.saving.set(true);
    try {
      await firstValueFrom(this.clinicService.updateMyClinic(this.form.getRawValue()));
      this.form.markAsPristine();
      this.snackBar.open('Datos de la clínica actualizados', 'Cerrar', { duration: 3000 });
    } catch (err) {
      this.snackBar.open(errorDetail(err, 'No se pudieron guardar los datos'), 'Cerrar', { duration: 4500 });
    } finally {
      this.saving.set(false);
    }
  }

  // ---- Sedes y consultorios ------------------------------------------------

  private async reloadRooms(): Promise<void> {
    const [branches, operatories] = await Promise.all([
      firstValueFrom(this.clinicService.listBranches()),
      firstValueFrom(this.clinicService.listOperatories()),
    ]);
    this.branches.set(branches);
    this.operatories.set(operatories);
  }

  async addBranch(): Promise<void> {
    const name = await promptText(this.dialog, {
      title: 'Nueva sede',
      label: 'Nombre de la sede',
      confirmLabel: 'Crear sede',
    });
    if (!name) return;
    await firstValueFrom(this.clinicService.createBranch({ name, is_main: this.branches().length === 0 }));
    await this.reloadRooms();
  }

  async renameBranch(branch: Branch): Promise<void> {
    const name = await promptText(this.dialog, { title: 'Renombrar sede', label: 'Nombre', initial: branch.name });
    if (!name || name === branch.name) return;
    await firstValueFrom(this.clinicService.updateBranch(branch.id, { name }));
    await this.reloadRooms();
  }

  async editBranchAddress(branch: Branch): Promise<void> {
    const address = await promptText(this.dialog, {
      title: `Dirección de ${branch.name}`,
      label: 'Dirección',
      initial: branch.address ?? '',
    });
    if (address === null) return;
    await firstValueFrom(this.clinicService.updateBranch(branch.id, { address }));
    await this.reloadRooms();
  }

  async makeMain(branch: Branch): Promise<void> {
    // Solo una principal: se quita la marca a la anterior antes de ponerla.
    for (const other of this.branches().filter((b) => b.is_main && b.id !== branch.id)) {
      await firstValueFrom(this.clinicService.updateBranch(other.id, { is_main: false }));
    }
    await firstValueFrom(this.clinicService.updateBranch(branch.id, { is_main: true }));
    await this.reloadRooms();
  }

  async deleteBranch(branch: Branch): Promise<void> {
    const ok = await confirmAction(this.dialog, {
      title: `¿Eliminar la sede "${branch.name}"?`,
      message: 'Solo se puede si ya no tiene consultorios.',
      confirmLabel: 'Eliminar',
      danger: true,
    });
    if (!ok) return;
    try {
      await firstValueFrom(this.clinicService.deleteBranch(branch.id));
      await this.reloadRooms();
    } catch (err) {
      this.snackBar.open(errorDetail(err, 'No se pudo eliminar la sede'), 'Cerrar', { duration: 4500 });
    }
  }

  async addRoom(branch: Branch): Promise<void> {
    const name = await promptText(this.dialog, {
      title: `Nuevo consultorio en ${branch.name}`,
      label: 'Nombre (ej. Sillón 1)',
      confirmLabel: 'Agregar',
    });
    if (!name) return;
    await firstValueFrom(this.clinicService.createOperatory({ branch_id: branch.id, name }));
    await this.reloadRooms();
  }

  async renameRoom(room: Operatory): Promise<void> {
    const name = await promptText(this.dialog, { title: 'Renombrar consultorio', label: 'Nombre', initial: room.name });
    if (!name || name === room.name) return;
    await firstValueFrom(this.clinicService.updateOperatory(room.id, { name }));
    await this.reloadRooms();
  }

  async toggleRoom(room: Operatory): Promise<void> {
    await firstValueFrom(this.clinicService.updateOperatory(room.id, { is_active: !room.is_active }));
    await this.reloadRooms();
  }

  async deleteRoom(room: Operatory): Promise<void> {
    const ok = await confirmAction(this.dialog, {
      title: `¿Eliminar "${room.name}"?`,
      message: 'Si ya tiene citas registradas no se podrá: en ese caso, desactívelo.',
      confirmLabel: 'Eliminar',
      danger: true,
    });
    if (!ok) return;
    try {
      await firstValueFrom(this.clinicService.deleteOperatory(room.id));
      await this.reloadRooms();
    } catch (err) {
      this.snackBar.open(errorDetail(err, 'No se pudo eliminar el consultorio'), 'Cerrar', { duration: 4500 });
    }
  }
}
