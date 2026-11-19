import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, shareReplay } from 'rxjs';

import { environment } from '../../../environments/environment';
import { PaymentMethodCode } from '../models/finance.models';
import {
  OrthoCase,
  OrthoCaseDetail,
  OrthoCaseFields,
  OrthoCaseList,
  OrthoControlFields,
  OrthoFilters,
  OrthoOptions,
} from '../models/orthodontics.models';

@Injectable({ providedIn: 'root' })
export class OrthodonticsService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/orthodontics`;
  private options$: Observable<OrthoOptions> | null = null;

  options(): Observable<OrthoOptions> {
    this.options$ ??= this.http.get<OrthoOptions>(`${this.base}/options`).pipe(shareReplay(1));
    return this.options$;
  }

  list(filters: OrthoFilters = {}): Observable<OrthoCaseList> {
    let params = new HttpParams();
    for (const [k, v] of Object.entries(filters)) {
      if (v !== undefined && v !== null && v !== '') params = params.set(k, String(v));
    }
    return this.http.get<OrthoCaseList>(`${this.base}/cases`, { params });
  }

  forPatient(patientId: string): Observable<OrthoCase[]> {
    return this.http.get<OrthoCase[]>(`${environment.apiUrl}/patients/${patientId}/orthodontics`);
  }

  get(id: string): Observable<OrthoCaseDetail> {
    return this.http.get<OrthoCaseDetail>(`${this.base}/cases/${id}`);
  }

  create(patientId: string, body: OrthoCaseFields): Observable<OrthoCaseDetail> {
    return this.http.post<OrthoCaseDetail>(`${this.base}/cases`, { patient_id: patientId, ...body });
  }

  update(id: string, body: OrthoCaseFields): Observable<OrthoCaseDetail> {
    return this.http.patch<OrthoCaseDetail>(`${this.base}/cases/${id}`, body);
  }

  remove(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/cases/${id}`);
  }

  addControl(caseId: string, body: OrthoControlFields): Observable<OrthoCaseDetail> {
    return this.http.post<OrthoCaseDetail>(`${this.base}/cases/${caseId}/controls`, body);
  }

  generate(
    caseId: string,
    body: { count: number; first_on: string; amount: string; every_days: number | null },
  ): Observable<OrthoCaseDetail> {
    return this.http.post<OrthoCaseDetail>(`${this.base}/cases/${caseId}/controls/generate`, body);
  }

  updateControl(id: string, body: OrthoControlFields): Observable<OrthoCaseDetail> {
    return this.http.patch<OrthoCaseDetail>(`${this.base}/controls/${id}`, body);
  }

  removeControl(id: string): Observable<OrthoCaseDetail> {
    return this.http.delete<OrthoCaseDetail>(`${this.base}/controls/${id}`);
  }

  pay(
    controlId: string,
    body: { amount: string; method: PaymentMethodCode; reference: string | null; received_on: string | null; notes: string | null },
  ): Observable<OrthoCaseDetail> {
    return this.http.post<OrthoCaseDetail>(`${this.base}/controls/${controlId}/payments`, body);
  }

  exportUrl(caseId: string, kind: 'csv' | 'pdf'): string {
    return `${this.base}/cases/${caseId}/export.${kind}`;
  }

  download(caseId: string, kind: 'csv' | 'pdf'): Observable<Blob> {
    return this.http.get(this.exportUrl(caseId, kind), { responseType: 'blob' });
  }
}
