export interface DateRange {
  date_from: string;
  date_to: string;
}

export interface NamedAmount {
  key: string;
  label: string;
  amount: string;
  count: number;
}

export interface AgingBucket {
  label: string;
  amount: string;
  count: number;
}

export interface FinancialReport {
  range: DateRange;
  collected: string;
  charged: string;
  payment_count: number;
  by_method: NamedAmount[];
  by_professional: NamedAmount[];
  daily: { day: string; amount: string }[];
  /** As of today, not of the range: a debt belongs to now, not to the month
   *  in which it was billed. */
  outstanding_total: string;
  aging: AgingBucket[];
  voided_total: string;
  voided_count: number;
}

export interface BudgetConversion {
  accepted_count: number;
  accepted_amount: string;
  rejected_count: number;
  rejected_amount: string;
  pending_count: number;
  pending_amount: string;
  /** Accepted over DECIDED budgets; null when none were decided. */
  conversion_rate: number | null;
}

export interface ClinicalReport {
  range: DateRange;
  treatments_completed: number;
  by_treatment: NamedAmount[];
  by_professional: NamedAmount[];
  top_diagnoses: NamedAmount[];
  budgets: BudgetConversion;
}

export interface AppointmentReport {
  range: DateRange;
  total: number;
  by_status: NamedAmount[];
  by_professional: NamedAmount[];
  by_weekday: NamedAmount[];
  concluded: number;
  attended: number;
  no_show: number;
  cancelled: number;
  /** null when nothing concluded — unknown, not zero. */
  no_show_rate: number | null;
  cancellation_rate: number | null;
}

export interface PatientReport {
  range: DateRange;
  new_patients: number;
  total_active: number;
  by_month: NamedAmount[];
  by_sex: NamedAmount[];
  by_age_band: NamedAmount[];
  seen_last_12m: number;
  dormant: number;
}

export interface ReportSummary {
  range: DateRange;
  collected: string;
  outstanding: string;
  appointments: number;
  no_show_rate: number | null;
  new_patients: number;
  treatments_completed: number;
}

export type ReportKind = 'financial' | 'clinical' | 'appointments' | 'patients';

export const REPORT_TABS: { kind: ReportKind; label: string; icon: string }[] = [
  { kind: 'financial', label: 'Financiero', icon: 'payments' },
  { kind: 'clinical', label: 'Clínico', icon: 'medical_services' },
  { kind: 'appointments', label: 'Agenda', icon: 'event' },
  { kind: 'patients', label: 'Pacientes', icon: 'groups' },
];

/** A rate that is unknown prints as a dash, never as 0 % — the two mean very
 *  different things to whoever reads the report. */
export function formatRate(value: number | null): string {
  return value === null ? '—' : `${value} %`;
}
