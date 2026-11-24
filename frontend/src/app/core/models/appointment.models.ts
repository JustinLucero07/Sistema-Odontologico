export type AppointmentStatus =
  | 'programada'
  | 'confirmada'
  | 'en_espera'
  | 'en_atencion'
  | 'atendida'
  | 'cancelada'
  | 'no_asistio';

export type ReminderChannel = 'whatsapp' | 'email' | 'sms';

export interface AppointmentReminder {
  id: string;
  channel: ReminderChannel;
  offset_minutes: number;
  scheduled_for: string;
  status: 'pendiente' | 'enviado' | 'fallido' | 'cancelado';
  sent_at: string | null;
}

export interface Appointment {
  id: string;
  patient_id: string;
  patient_name: string;
  professional_id: string;
  professional_name: string;
  operatory_id: string | null;
  treatment_id: string | null;
  treatment_name: string | null;
  treatment_plan_item_id: string | null;
  starts_at: string;
  ends_at: string;
  duration_minutes: number;
  status: AppointmentStatus;
  color_hex: string | null;
  notes: string | null;
  cancellation_reason: string | null;
  reminders: AppointmentReminder[];
}

export interface AppointmentCreate {
  patient_id: string;
  professional_id: string;
  operatory_id?: string | null;
  treatment_id?: string | null;
  starts_at: string;
  ends_at: string;
  notes?: string | null;
  reminder_channels?: ReminderChannel[];
}

export const APPOINTMENT_STATUS_LABELS: Record<AppointmentStatus, string> = {
  programada: 'Programada',
  confirmada: 'Confirmada',
  en_espera: 'En espera',
  en_atencion: 'En atención',
  atendida: 'Atendida',
  cancelada: 'Cancelada',
  no_asistio: 'No asistió',
};

export const APPOINTMENT_STATUS_COLORS: Record<AppointmentStatus, string> = {
  programada: 'var(--status-programada)',
  confirmada: 'var(--status-confirmada)',
  en_espera: 'var(--status-en-espera)',
  en_atencion: 'var(--status-en-atencion)',
  atendida: 'var(--status-atendida)',
  cancelada: 'var(--status-cancelada)',
  no_asistio: 'var(--status-no-asistio)',
};
