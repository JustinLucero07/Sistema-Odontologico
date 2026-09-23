import { DatePipe } from '@angular/common';
import { Component, Input, OnChanges, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { firstValueFrom } from 'rxjs';

import {
  APPOINTMENT_STATUS_COLORS,
  APPOINTMENT_STATUS_LABELS,
  Appointment,
} from '../../core/models/appointment.models';
import { AppointmentsService } from '../../core/services/appointments.service';
import { AuthService } from '../../core/auth/auth.service';
import { promptText } from '../../shared/confirm-dialog/prompt-dialog.component';

@Component({
  selector: 'app-patient-appointments-tab',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatIconModule, MatTooltipModule, RouterLink],
  templateUrl: './patient-appointments-tab.component.html',
  styleUrl: './patient-appointments-tab.component.scss',
})
export class PatientAppointmentsTabComponent implements OnChanges {
  @Input({ required: true }) patientId!: string;

  private readonly appointmentsService = inject(AppointmentsService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  readonly auth = inject(AuthService);

  readonly statusLabels = APPOINTMENT_STATUS_LABELS;
  readonly appointments = signal<Appointment[]>([]);

  async ngOnChanges(): Promise<void> {
    if (!this.patientId) return;
    this.appointments.set(await firstValueFrom(this.appointmentsService.listForPatient(this.patientId)));
  }

  canChange(appointment: Appointment): boolean {
    return (
      this.auth.hasPermission('appointments:write') &&
      !['atendida', 'cancelada', 'no_asistio'].includes(appointment.status)
    );
  }

  /** Cancelar pide el motivo: sin él, nadie sabe después si fue la clínica o el paciente. */
  async cancel(appointment: Appointment): Promise<void> {
    const reason = await promptText(this.dialog, {
      title: 'Cancelar cita',
      message: 'La cita queda en el historial como cancelada y libera el horario.',
      label: 'Motivo de la cancelación',
      minLength: 3,
      confirmLabel: 'Cancelar cita',
      danger: true,
    });
    if (!reason) return;
    await firstValueFrom(this.appointmentsService.updateStatus(appointment.id, 'cancelada', reason));
    this.snackBar.open('Cita cancelada', 'Cerrar', { duration: 3000 });
    await this.ngOnChanges();
  }

  statusColor(appointment: Appointment): string {
    return APPOINTMENT_STATUS_COLORS[appointment.status];
  }

  get upcoming(): Appointment[] {
    const now = Date.now();
    return this.appointments().filter(
      (a) => new Date(a.starts_at).getTime() >= now && a.status !== 'cancelada',
    );
  }

  get past(): Appointment[] {
    const now = Date.now();
    return this.appointments().filter(
      (a) => new Date(a.starts_at).getTime() < now || a.status === 'cancelada',
    );
  }
}
