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
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
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
import { PatientsService } from '../../core/services/patients.service';
import { ClinicService } from '../../core/services/clinic.service';
import { TreatmentsService } from '../../core/services/treatments.service';
import { PatientPickerComponent } from '../../shared/patient-picker/patient-picker.component';

/** Visible working day. Appointments outside it still load, they just sit at
 * the edge of the grid rather than being hidden. */
const START_HOUR = 7;
const END_HOUR = 21;
// 72 px por hora: una cita de 30 min mide 36 px, suficiente para leerse.
const HOUR_HEIGHT = 72;

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
    RouterLink,
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
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly patientsService = inject(PatientsService);

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
  /** Cita que se reprograma; null cuando el formulario agenda una nueva. */
  readonly editingAppointment = signal<Appointment | null>(null);

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

    // `?nueva=1` abre el formulario directamente, y `&paciente=<id>` lo trae
    // ya elegido: así «Agendar cita» desde la ficha o desde la barra superior
    // no obliga a buscar otra vez a quien se acaba de tener delante.
    const params = this.route.snapshot.queryParamMap;
    if (params.get('nueva')) {
      const patientId = params.get('paciente');
      let patient: PatientListItem | null = null;
      if (patientId) {
        try {
          const p = await firstValueFrom(this.patientsService.getPatient(patientId));
          patient = {
            id: p.id,
            first_name: p.first_name,
            last_name: p.last_name,
            national_id: p.national_id ?? null,
            age: null,
            phone: p.phone ?? null,
            whatsapp: p.whatsapp ?? null,
          };
        } catch {
          // Paciente inexistente o sin permiso: se abre el formulario vacío.
        }
      }
      this.newAppointment(patient);
      // Se limpia la URL para que recargar la página no vuelva a abrirlo.
      this.router.navigate([], { queryParams: {}, replaceUrl: true });
    }

    // `?editar=<id>` abre esa cita para reprogramarla, en su semana.
    const editId = params.get('editar');
    if (editId) {
      try {
        const appointment = await firstValueFrom(this.appointmentsService.get(editId));
        this.anchorDate.set(startOfDay(new Date(appointment.starts_at)));
        await this.reload();
        this.editAppointment(appointment);
      } catch {
        this.snackBar.open('No se encontró la cita', 'Cerrar', { duration: 3000 });
      }
      this.router.navigate([], { queryParams: {}, replaceUrl: true });
    }
  }

  /** Abre el formulario en el próximo hueco razonable: la siguiente media hora
   *  de hoy, o mañana a las 9:00 si la jornada ya terminó. Antes la única vía
   *  era tocar un hueco del calendario, y nada en la pantalla lo decía. */
  newAppointment(patient: PatientListItem | null = null): void {
    const now = new Date();
    const next = new Date(now);
    next.setSeconds(0, 0);
    next.setMinutes(now.getMinutes() < 30 ? 30 : 60);
    if (next.getHours() >= 20 || next.getHours() < 7) {
      next.setDate(next.getDate() + (next.getHours() >= 20 ? 1 : 0));
      next.setHours(9, 0, 0, 0);
    }
    this.openSlot(next, next.getHours());
    this.form.patchValue({
      time: `${String(next.getHours()).padStart(2, '0')}:${String(next.getMinutes()).padStart(2, '0')}`,
    });
    if (patient) this.formPatient.set(patient);
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
    this.editingAppointment.set(null);
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

  /** Una cita atendida o cancelada ya es historia: no se mueve. */
  canReschedule(appointment: Appointment): boolean {
    return this.canEdit() && !['atendida', 'cancelada', 'no_asistio'].includes(appointment.status);
  }

  editAppointment(appointment: Appointment): void {
    const start = new Date(appointment.starts_at);
    const [first, ...rest] = appointment.patient_name.split(' ');
    this.editingAppointment.set(appointment);
    this.formError.set(null);
    // Solo para mostrar el nombre: el paciente de una cita no se cambia.
    this.formPatient.set({ id: appointment.patient_id, first_name: first, last_name: rest.join(' ') } as PatientListItem);
    this.form.reset({
      professional_id: appointment.professional_id,
      treatment_id: appointment.treatment_id ?? '',
      date: toDateInput(start),
      time: `${String(start.getHours()).padStart(2, '0')}:${String(start.getMinutes()).padStart(2, '0')}`,
      duration: appointment.duration_minutes,
      notes: appointment.notes ?? '',
      remind_whatsapp: false,
      remind_email: false,
    });
    this.selected.set(null);
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

      const editing = this.editingAppointment();
      if (editing) {
        await firstValueFrom(
          this.appointmentsService.update(editing.id, {
            professional_id: value.professional_id,
            treatment_id: value.treatment_id || null,
            starts_at: start.toISOString(),
            ends_at: end.toISOString(),
            notes: value.notes || null,
          }),
        );
        this.formOpen.set(false);
        this.editingAppointment.set(null);
        this.snackBar.open('Cita actualizada. Los recordatorios se movieron a la nueva hora.', 'Cerrar', {
          duration: 3500,
        });
        await this.reload();
        return;
      }
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
