import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import {
  APPOINTMENT_STATUS_COLORS,
  APPOINTMENT_STATUS_LABELS,
  Appointment,
  AppointmentStatus,
  ReminderChannel,
} from '../../core/models/appointment.models';
import { PatientListItem } from '../../core/models/patient.models';
import { Professional } from '../../core/models/clinic.models';
import { Treatment } from '../../core/models/treatment.models';
import { AppointmentsService } from '../../core/services/appointments.service';
import { ClinicService } from '../../core/services/clinic.service';
import { TreatmentsService } from '../../core/services/treatments.service';
import { PatientPickerComponent } from '../../shared/patient-picker/patient-picker.component';

/** Visible working day. Appointments outside it still load, they just sit at
 * the edge of the grid rather than being hidden. */
const START_HOUR = 7;
const END_HOUR = 21;
const HOUR_HEIGHT = 56;

interface PositionedAppointment {
  appointment: Appointment;
  top: number;
  height: number;
  color: string;
}

interface DayColumn {
  date: Date;
  label: string;
  weekday: string;
  isToday: boolean;
  appointments: PositionedAppointment[];
}

@Component({
  selector: 'app-agenda',
  standalone: true,
  imports: [
    DatePipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    PatientPickerComponent,
  ],
  templateUrl: './agenda.component.html',
  styleUrl: './agenda.component.scss',
})
export class AgendaComponent implements OnInit {
  private readonly appointmentsService = inject(AppointmentsService);
  private readonly clinicService = inject(ClinicService);
  private readonly treatmentsService = inject(TreatmentsService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);

  readonly statusLabels = APPOINTMENT_STATUS_LABELS;
  readonly statusOptions = Object.keys(APPOINTMENT_STATUS_LABELS) as AppointmentStatus[];
  readonly hourHeight = HOUR_HEIGHT;
  readonly hours = Array.from({ length: END_HOUR - START_HOUR }, (_, i) => START_HOUR + i);

  readonly canEdit = computed(() => this.auth.hasPermission('appointments:write'));

  readonly view = signal<'day' | 'week'>('week');
  readonly anchorDate = signal(startOfDay(new Date()));
  readonly professionals = signal<Professional[]>([]);
  readonly treatments = signal<Treatment[]>([]);
  readonly professionalFilter = signal<string | null>(null);
  readonly appointments = signal<Appointment[]>([]);
  readonly loading = signal(false);

  readonly selected = signal<Appointment | null>(null);
  readonly formOpen = signal(false);
  readonly formPatient = signal<PatientListItem | null>(null);
  readonly saving = signal(false);
  readonly formError = signal<string | null>(null);

  readonly form = this.fb.nonNullable.group({
    professional_id: ['', Validators.required],
    treatment_id: [''],
    date: ['', Validators.required],
    time: ['', Validators.required],
    duration: [30, [Validators.required, Validators.min(5)]],
    notes: [''],
    remind_whatsapp: [true],
    remind_email: [false],
  });

  readonly columns = computed<DayColumn[]>(() => {
    const days = this.view() === 'day' ? [this.anchorDate()] : weekDays(this.anchorDate());
    const today = startOfDay(new Date()).getTime();

    return days.map((date) => {
      const dayStart = date.getTime();
      const dayEnd = dayStart + 24 * 60 * 60 * 1000;

      const positioned = this.appointments()
        .filter((a) => {
          const start = new Date(a.starts_at).getTime();
          return start >= dayStart && start < dayEnd;
        })
        .map((appointment) => {
          const start = new Date(appointment.starts_at);
          const minutesFromGridStart =
            start.getHours() * 60 + start.getMinutes() - START_HOUR * 60;
          return {
            appointment,
            top: (minutesFromGridStart / 60) * HOUR_HEIGHT,
            height: Math.max((appointment.duration_minutes / 60) * HOUR_HEIGHT, 22),
            color: APPOINTMENT_STATUS_COLORS[appointment.status],
          };
        });

      return {
        date,
        label: date.toLocaleDateString('es', { day: 'numeric', month: 'short' }),
        weekday: date.toLocaleDateString('es', { weekday: 'short' }),
        isToday: date.getTime() === today,
        appointments: positioned,
      };
    });
  });

  readonly rangeLabel = computed(() => {
    const cols = this.columns();
    if (cols.length === 1) {
      return cols[0].date.toLocaleDateString('es', { weekday: 'long', day: 'numeric', month: 'long' });
    }
    const first = cols[0].date;
    const last = cols[cols.length - 1].date;
    return `${first.toLocaleDateString('es', { day: 'numeric', month: 'short' })} – ${last.toLocaleDateString('es', { day: 'numeric', month: 'short', year: 'numeric' })}`;
  });

  async ngOnInit(): Promise<void> {
    const [professionals, treatments] = await Promise.all([
      firstValueFrom(this.clinicService.listProfessionals()),
      this.auth.hasPermission('treatments:read')
        ? firstValueFrom(this.treatmentsService.list())
        : Promise.resolve([] as Treatment[]),
    ]);
    this.professionals.set(professionals);
    this.treatments.set(treatments);
    await this.reload();
  }

  async reload(): Promise<void> {
    this.loading.set(true);
    try {
      const cols = this.view() === 'day' ? [this.anchorDate()] : weekDays(this.anchorDate());
      const from = cols[0];
      const to = new Date(cols[cols.length - 1].getTime() + 24 * 60 * 60 * 1000);
      this.appointments.set(
        await firstValueFrom(this.appointmentsService.list(from, to, this.professionalFilter())),
      );
    } finally {
      this.loading.set(false);
    }
  }

  async setView(view: 'day' | 'week'): Promise<void> {
    this.view.set(view);
    await this.reload();
  }

  async setProfessionalFilter(id: string | null): Promise<void> {
    this.professionalFilter.set(id || null);
    await this.reload();
  }

  async move(direction: -1 | 1): Promise<void> {
    const step = this.view() === 'day' ? 1 : 7;
    const next = new Date(this.anchorDate());
    next.setDate(next.getDate() + direction * step);
    this.anchorDate.set(startOfDay(next));
    await this.reload();
  }

  async goToday(): Promise<void> {
    this.anchorDate.set(startOfDay(new Date()));
    await this.reload();
  }

  // ---- Booking ----------------------------------------------------------

  openSlot(date: Date, hour: number): void {
    if (!this.canEdit()) return;
    this.formError.set(null);
    this.formPatient.set(null);
    this.form.reset({
      professional_id: this.professionalFilter() ?? this.professionals()[0]?.id ?? '',
      treatment_id: '',
      date: toDateInput(date),
      time: `${String(hour).padStart(2, '0')}:00`,
      duration: 30,
      notes: '',
      remind_whatsapp: true,
      remind_email: false,
    });
    this.formOpen.set(true);
  }

  closeForm(): void {
    this.formOpen.set(false);
  }

  statusColor(status: AppointmentStatus): string {
    return APPOINTMENT_STATUS_COLORS[status];
  }

  async submitAppointment(): Promise<void> {
    const patient = this.formPatient();
    if (!patient) {
      this.formError.set('Selecciona un paciente.');
      return;
    }
    if (this.form.invalid || this.saving()) return;

    this.saving.set(true);
    this.formError.set(null);
    try {
      const value = this.form.getRawValue();
      const start = new Date(`${value.date}T${value.time}`);
      const end = new Date(start.getTime() + value.duration * 60 * 1000);
      const channels: ReminderChannel[] = [];
      if (value.remind_whatsapp) channels.push('whatsapp');
      if (value.remind_email) channels.push('email');

      await firstValueFrom(
        this.appointmentsService.create({
          patient_id: patient.id,
          professional_id: value.professional_id,
          treatment_id: value.treatment_id || null,
          starts_at: start.toISOString(),
          ends_at: end.toISOString(),
          notes: value.notes || null,
          reminder_channels: channels,
        }),
      );
      this.formOpen.set(false);
      this.snackBar.open('Cita agendada', 'Cerrar', { duration: 3000 });
      await this.reload();
    } catch (error: unknown) {
      const detail = (error as { error?: { detail?: string } })?.error?.detail;
      this.formError.set(detail ?? 'No se pudo agendar la cita.');
    } finally {
      this.saving.set(false);
    }
  }

  select(appointment: Appointment): void {
    this.selected.set(appointment);
  }

  closeDetail(): void {
    this.selected.set(null);
  }

  async changeStatus(appointment: Appointment, status: AppointmentStatus): Promise<void> {
    const updated = await firstValueFrom(this.appointmentsService.updateStatus(appointment.id, status));
    this.selected.set(updated);
    await this.reload();
  }

  pendingReminders(appointment: Appointment): number {
    return appointment.reminders.filter((r) => r.status === 'pendiente').length;
  }
}

function startOfDay(date: Date): Date {
  const copy = new Date(date);
  copy.setHours(0, 0, 0, 0);
  return copy;
}

/** Monday-first week containing the given date. */
function weekDays(anchor: Date): Date[] {
  const monday = startOfDay(anchor);
  const weekday = (monday.getDay() + 6) % 7;
  monday.setDate(monday.getDate() - weekday);
  return Array.from({ length: 7 }, (_, i) => {
    const day = new Date(monday);
    day.setDate(monday.getDate() + i);
    return day;
  });
}

function toDateInput(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
}
