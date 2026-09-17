import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Odontogram, OdontogramCreate, OdontogramSummary } from '../models/odontogram.models';

@Injectable({ providedIn: 'root' })
export class OdontogramService {
  private readonly http = inject(HttpClient);

  private base(patientId: string): string {
    return `${environment.apiUrl}/patients/${patientId}/odontogram`;
  }

  getLatest(patientId: string): Observable<Odontogram | null> {
    return this.http.get<Odontogram | null>(this.base(patientId));
  }

  getVersion(patientId: string, odontogramId: string): Observable<Odontogram> {
    return this.http.get<Odontogram>(`${this.base(patientId)}/${odontogramId}`);
  }

  listVersions(patientId: string): Observable<OdontogramSummary[]> {
    return this.http.get<OdontogramSummary[]>(`${this.base(patientId)}/versions`);
  }

  createSnapshot(patientId: string, payload: OdontogramCreate): Observable<Odontogram> {
    return this.http.post<Odontogram>(this.base(patientId), payload);
  }
}
