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
  legal_rep_name?: string | null;
  dpo_name?: string | null;
  dpo_email?: string | null;
  health_permit_number?: string | null;
  record_retention_years?: number;
  privacy_extra?: string | null;
  terms_version?: string;
  logo_data?: string | null;
  primary_color?: string | null;
  slogan?: string | null;
  document_footer?: string | null;
}

export interface LegalDocument {
  code: 'terminos' | 'encargo';
  title: string;
  version: string;
  sections: { title: string; paragraphs: string[] }[];
}

export interface Option {
  code: string;
  label: string;
}

export interface LegalCatalogs {
  rights_kinds: Option[];
  rights_statuses: Option[];
  tax_regimes: Option[];
}

export interface RightsRequest {
  id: string;
  patient_id: string | null;
  patient_name: string | null;
  requester_name: string;
  requester_id_number: string | null;
  contact: string | null;
  kind: string;
  kind_label: string;
  details: string | null;
  received_on: string;
  due_on: string;
  status: string;
  status_label: string;
  response: string | null;
  resolved_on: string | null;
  overdue: boolean;
  days_left: number | null;
}

export type RightsRequestInput = Pick<
  RightsRequest,
  'patient_id' | 'requester_name' | 'requester_id_number' | 'contact' | 'kind' | 'details' | 'received_on' | 'status' | 'response'
>;

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

  /** Tras cambiar los datos legales, el próximo aviso se arma con los nuevos. */
  refreshController(): void {
    this.controller$ = null;
  }

  getDocument(code: LegalDocument['code']): Observable<LegalDocument> {
    return this.http.get<LegalDocument>(`${this.api}/legal/documents/${code}`);
  }

  getCatalogs(): Observable<LegalCatalogs> {
    return this.http.get<LegalCatalogs>(`${this.api}/legal/catalogs`);
  }

  listRequests(): Observable<RightsRequest[]> {
    return this.http.get<RightsRequest[]>(`${this.api}/legal/requests`);
  }

  saveRequest(data: RightsRequestInput, id?: string): Observable<RightsRequest> {
    return id
      ? this.http.put<RightsRequest>(`${this.api}/legal/requests/${id}`, data)
      : this.http.post<RightsRequest>(`${this.api}/legal/requests`, data);
  }

  deleteRequest(id: string): Observable<void> {
    return this.http.delete<void>(`${this.api}/legal/requests/${id}`);
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
