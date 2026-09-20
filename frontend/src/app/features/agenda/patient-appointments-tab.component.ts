import { DatePipe } from '@angular/common';
import { Component, Input, OnChanges, inject, signal } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { firstValueFrom } from 'rxjs';

import {
  APPOINTMENT_STATUS_COLORS,
  APPOINTMENT_STATUS_LABELS,
  Appointment,
} from '../../core/models/appointment.models';
import { AppointmentsService } from '../../core/services/appointments.service';

@Component({
  selector: 'app-patient-appointments-tab',
  standalone: true,
  imports: [DatePipe, MatIconModule],
  templateUrl: './patient-appointments-tab.component.html',
  styleUrl: './patient-appointments-tab.component.scss',
})
export class PatientAppointmentsTabComponent implements OnChanges {
  @Input({ required: true }) patientId!: string;

  private readonly appointmentsService = inject(AppointmentsService);

  readonly statusLabels = APPOINTMENT_STATUS_LABELS;
  readonly appointments = signal<Appointment[]>([]);

  async ngOnChanges(): Promise<void> {
    if (!this.patientId) return;
    this.appointments.set(await firstValueFrom(this.appointmentsService.listForPatient(this.patientId)));
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
