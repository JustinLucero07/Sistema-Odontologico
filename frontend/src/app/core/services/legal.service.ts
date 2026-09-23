import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, shareReplay } from 'rxjs';

import { environment } from '../../../environments/environment';

/** La clínica como responsable del tratamiento de datos. */
export interface LegalController {
  name: string;
  legal_name: string | null;
  tax_id: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  privacy_policy_version: string;
  confidentiality_version: string;
}

export type ConsentKind = 'aviso_privacidad' | 'comunicaciones';
export type ConsentMethod = 'firma_presencial' | 'verbal' | 'digital';

export interface DataConsent {
  id: string;
  kind: ConsentKind;
  granted: boolean;
  policy_version: string;
  method: ConsentMethod;
  signed_by_name: string | null;
  notes: string | null;
  recorded_by_name: string | null;
  recorded_at: string;
}

export interface PrivacyStatus {
  current_policy_version: string;
  privacy_notice: DataConsent | null;
  communications: DataConsent | null;
  notice_outdated: boolean;
  history: DataConsent[];
}

export interface AccessEntry {
  at: string;
  action: string;
  user_name: string | null;
}

export const CONSENT_METHOD_LABELS: Record<ConsentMethod, string> = {
  firma_presencial: 'Firmado en la clínica',
  verbal: 'De palabra, ante el personal',
  digital: 'Por medio digital',
};

@Injectable({ providedIn: 'root' })
export class LegalService {
  private readonly http = inject(HttpClient);
  private readonly api = environment.apiUrl;

  /** Cambia muy poco: se pide una vez por sesión. */
  private controller$: Observable<LegalController> | null = null;

  getController(): Observable<LegalController> {
    this.controller$ ??= this.http.get<LegalController>(`${this.api}/legal/controller`).pipe(shareReplay(1));
    return this.controller$;
  }

  getPrivacy(patientId: string): Observable<PrivacyStatus> {
    return this.http.get<PrivacyStatus>(`${this.api}/patients/${patientId}/privacy`);
  }

  recordConsent(
    patientId: string,
    payload: { kind: ConsentKind; granted?: boolean; method: ConsentMethod; signed_by_name?: string | null },
  ): Observable<DataConsent> {
    return this.http.post<DataConsent>(`${this.api}/patients/${patientId}/privacy/consents`, payload);
  }

  getAccessLog(patientId: string): Observable<AccessEntry[]> {
    return this.http.get<AccessEntry[]>(`${this.api}/patients/${patientId}/privacy/access-log`);
  }

  exportPatient(patientId: string): Observable<Blob> {
    return this.http.get(`${this.api}/patients/${patientId}/privacy/export`, { responseType: 'blob' });
  }

  acceptConfidentiality(): Observable<void> {
    return this.http.post<void>(`${this.api}/auth/confidentiality`, {});
  }
}
