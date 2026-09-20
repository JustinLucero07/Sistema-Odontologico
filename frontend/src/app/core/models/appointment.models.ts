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

/** Colour per state, so a glance at the agenda tells you where each patient is
 * in the visit, independent of the professional's own colour.
 *
 * These resolve to CSS custom properties rather than literal hexes, because the
 * day and night sets are *chosen* separately — the real values live in
 * `styles.scss`. A flipped palette gives dead mid-tones, and three of the day
 * colours fall under 3:1 against the night surface.
 *
 * Neither set is picked by eye. Both are run through the data-viz validator:
 * worst adjacent pair ΔE 9.5 protan / 21.3 normal in light, 8.6 deutan / 21.3
 * normal in dark, every step above the chroma floor and (in dark) above 3:1
 * against the surface. Two earlier defects the validator caught: "cancelada"
 * and "no asistió" sat at ΔE 8.6 — two bad outcomes that looked alike even to
 * full-colour vision — and "atendida" was a neutral grey that fell below the
 * chroma floor, reading as absent data rather than as a state.
 *
 * Every place these colours appear also shows the status label, so state is
 * never conveyed by colour alone. */
export const APPOINTMENT_STATUS_COLORS: Record<AppointmentStatus, string> = {
  programada: 'var(--status-programada)',
  confirmada: 'var(--status-confirmada)',
  en_espera: 'var(--status-en-espera)',
  en_atencion: 'var(--status-en-atencion)',
  atendida: 'var(--status-atendida)',
  cancelada: 'var(--status-cancelada)',
  no_asistio: 'var(--status-no-asistio)',
};
