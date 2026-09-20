import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  Periodontogram,
  PeriodontogramCreate,
  PeriodontogramSummary,
} from '../models/periodontogram.models';

@Injectable({ providedIn: 'root' })
export class PeriodontogramService {
  private readonly http = inject(HttpClient);

  private base(patientId: string): string {
    return `${environment.apiUrl}/patients/${patientId}/periodontogram`;
  }

  getLatest(patientId: string): Observable<Periodontogram | null> {
    return this.http.get<Periodontogram | null>(this.base(patientId));
  }

  getVersions(patientId: string): Observable<PeriodontogramSummary[]> {
    return this.http.get<PeriodontogramSummary[]>(`${this.base(patientId)}/versions`);
  }

  getVersion(patientId: string, id: string): Observable<Periodontogram> {
    return this.http.get<Periodontogram>(`${this.base(patientId)}/${id}`);
  }

  /** Always a POST: an exam is never edited in place, so there is no update
   *  method to call by mistake. */
  create(patientId: string, payload: PeriodontogramCreate): Observable<Periodontogram> {
    return this.http.post<Periodontogram>(this.base(patientId), payload);
  }
}
