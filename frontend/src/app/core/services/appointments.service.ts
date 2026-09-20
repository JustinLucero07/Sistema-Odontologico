import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  Appointment,
  AppointmentCreate,
  AppointmentStatus,
} from '../models/appointment.models';

@Injectable({ providedIn: 'root' })
export class AppointmentsService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/appointments`;

  list(from: Date, to: Date, professionalId?: string | null): Observable<Appointment[]> {
    let params = new HttpParams().set('from', from.toISOString()).set('to', to.toISOString());
    if (professionalId) params = params.set('professional_id', professionalId);
    return this.http.get<Appointment[]>(this.base, { params });
  }

  listForPatient(patientId: string): Observable<Appointment[]> {
    return this.http.get<Appointment[]>(`${environment.apiUrl}/patients/${patientId}/appointments`);
  }

  create(payload: AppointmentCreate): Observable<Appointment> {
    return this.http.post<Appointment>(this.base, payload);
  }

  update(id: string, payload: Partial<AppointmentCreate>): Observable<Appointment> {
    return this.http.put<Appointment>(`${this.base}/${id}`, payload);
  }

  updateStatus(id: string, status: AppointmentStatus, reason?: string): Observable<Appointment> {
    return this.http.put<Appointment>(`${this.base}/${id}/status`, {
      status,
      cancellation_reason: reason ?? null,
    });
  }
}
