import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, shareReplay } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  Credit,
  CreditCreate,
  CreditDetail,
  CreditFrequency,
  CreditOptions,
  CreditPreview,
  CreditStatus,
  CreditSummary,
} from '../models/credit.models';

@Injectable({ providedIn: 'root' })
export class CreditsService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/credits`;
  private options$: Observable<CreditOptions> | null = null;

  getOptions(): Observable<CreditOptions> {
    this.options$ ??= this.http.get<CreditOptions>(`${this.base}/options`).pipe(shareReplay(1));
    return this.options$;
  }

  preview(p: {
    principal: string;
    installment_count: number;
    monthly_rate: string;
    frequency: CreditFrequency;
    first_due_on: string;
  }): Observable<CreditPreview> {
    return this.http.get<CreditPreview>(`${this.base}/preview`, { params: { ...p } });
  }

  list(status?: CreditStatus): Observable<Credit[]> {
    return this.http.get<Credit[]>(this.base, { params: status ? { status } : {} });
  }

  listForPatient(patientId: string): Observable<Credit[]> {
    return this.http.get<Credit[]>(`${environment.apiUrl}/patients/${patientId}/credits`);
  }

  summary(): Observable<CreditSummary> {
    return this.http.get<CreditSummary>(`${this.base}/summary`);
  }

  get(id: string): Observable<CreditDetail> {
    return this.http.get<CreditDetail>(`${this.base}/${id}`);
  }

  create(patientId: string, body: CreditCreate): Observable<CreditDetail> {
    return this.http.post<CreditDetail>(`${environment.apiUrl}/patients/${patientId}/credits`, body);
  }

  update(
    id: string,
    body: { guarantor_name: string | null; guarantor_id_number: string | null; guarantor_phone: string | null; notes: string | null },
  ): Observable<CreditDetail> {
    return this.http.put<CreditDetail>(`${this.base}/${id}`, body);
  }

  pay(
    id: string,
    body: { amount: string; method: string; reference?: string | null; notes?: string | null },
  ): Observable<CreditDetail> {
    return this.http.post<CreditDetail>(`${this.base}/${id}/payments`, body);
  }

  restructure(
    id: string,
    body: { installment_count: number; frequency: CreditFrequency; first_due_on: string },
  ): Observable<CreditDetail> {
    return this.http.post<CreditDetail>(`${this.base}/${id}/restructure`, body);
  }

  void(id: string, reason: string): Observable<CreditDetail> {
    return this.http.post<CreditDetail>(`${this.base}/${id}/void`, { reason });
  }
}
