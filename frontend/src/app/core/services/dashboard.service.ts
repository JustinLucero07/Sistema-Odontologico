import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AppointmentStatus } from '../models/appointment.models';

export interface DashboardSummary {
  total_patients: number;
  new_patients_30d: number;
  appointments_today: number;
  appointments_this_week: number;
  appointments_previous_week: number;
  treatments_pending: number;
  appointments_by_status: { status: AppointmentStatus; count: number }[];
  appointments_per_day: { date: string; count: number }[];
  budget_accepted_total: number;
  budget_awaiting_total: number;
}

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private readonly http = inject(HttpClient);

  getSummary(): Observable<DashboardSummary> {
    return this.http.get<DashboardSummary>(`${environment.apiUrl}/dashboard/summary`);
  }
}
