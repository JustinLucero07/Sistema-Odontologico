import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Treatment, TreatmentCreate } from '../models/treatment.models';

@Injectable({ providedIn: 'root' })
export class TreatmentsService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/treatments`;

  list(includeInactive = false): Observable<Treatment[]> {
    return this.http.get<Treatment[]>(this.base, { params: { include_inactive: includeInactive } });
  }

  create(payload: TreatmentCreate): Observable<Treatment> {
    return this.http.post<Treatment>(this.base, payload);
  }

  update(id: string, payload: Partial<TreatmentCreate & { is_active: boolean }>): Observable<Treatment> {
    return this.http.put<Treatment>(`${this.base}/${id}`, payload);
  }
}
