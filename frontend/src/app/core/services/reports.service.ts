import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  AppointmentReport,
  ClinicalReport,
  FinancialReport,
  PatientReport,
  ReportKind,
  ReportSummary,
} from '../models/report.models';

@Injectable({ providedIn: 'root' })
export class ReportsService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/reports`;

  private query(from: string, to: string): string {
    return `?date_from=${from}&date_to=${to}`;
  }

  getSummary(from: string, to: string): Observable<ReportSummary> {
    return this.http.get<ReportSummary>(`${this.base}/summary${this.query(from, to)}`);
  }

  getFinancial(from: string, to: string): Observable<FinancialReport> {
    return this.http.get<FinancialReport>(`${this.base}/financial${this.query(from, to)}`);
  }

  getClinical(from: string, to: string): Observable<ClinicalReport> {
    return this.http.get<ClinicalReport>(`${this.base}/clinical${this.query(from, to)}`);
  }

  getAppointments(from: string, to: string): Observable<AppointmentReport> {
    return this.http.get<AppointmentReport>(`${this.base}/appointments${this.query(from, to)}`);
  }

  getPatients(from: string, to: string): Observable<PatientReport> {
    return this.http.get<PatientReport>(`${this.base}/patients${this.query(from, to)}`);
  }

  /** Fetched as a blob through the interceptor rather than linked directly:
   *  a plain <a href> would leave without the bearer token. */
  downloadCsv(kind: ReportKind, from: string, to: string): Observable<Blob> {
    return this.http.get(`${this.base}/${kind}.csv${this.query(from, to)}`, {
      responseType: 'blob',
    });
  }
}
