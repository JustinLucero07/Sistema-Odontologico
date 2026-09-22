import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AppointmentStatus } from '../models/appointment.models';

export interface AgendaEntry {
  id: string;
  starts_at: string;
  ends_at: string;
  status: AppointmentStatus;
  patient_id: string;
  patient_name: string;
  professional_name: string;
  professional_color: string | null;
  treatment_name: string | null;
}

export interface BirthdayEntry {
  patient_id: string;
  name: string;
  turns: number;
  whatsapp: string | null;
}

/** Cada cifra es null cuando el usuario no puede ver ese módulo: no es "cero". */
export interface DashboardAttention {
  stock_alerts: number | null;
  lab_overdue: number | null;
  budgets_awaiting: number | null;
  birthdays: BirthdayEntry[] | null;
}

export interface DashboardSummary {
  /** El día de la clínica (su zona horaria), en ISO. */
  today: string;
  total_patients: number;
  new_patients_30d: number;
  appointments_today: number;
  appointments_this_week: number;
  appointments_previous_week: number;
  treatments_pending: number;
  appointments_by_status: { status: AppointmentStatus; count: number }[];
  appointments_per_day: { date: string; count: number }[];
  today_agenda: AgendaEntry[] | null;
  budget_accepted_total: number | null;
  budget_awaiting_total: number | null;
  income_month: string | null;
  income_previous_month_same_period: string | null;
  receivables_total: string | null;
  attention: DashboardAttention;
}

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private readonly http = inject(HttpClient);

  getSummary(): Observable<DashboardSummary> {
    return this.http.get<DashboardSummary>(`${environment.apiUrl}/dashboard/summary`);
  }
}
