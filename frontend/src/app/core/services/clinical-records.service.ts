import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  ClinicalEvolution,
  Consent,
  ConsentCreate,
  ConsentTemplate,
  EvolutionCreate,
  PatientDocument,
  Prescription,
  PrescriptionCreate,
  ConsentLibraryItem,
  ConsentSignLink,
  ConsentSignPayload,
  PublicConsentView,
} from '../models/clinical-record.models';

@Injectable({ providedIn: 'root' })
export class ClinicalRecordsService {
  private readonly http = inject(HttpClient);
  private readonly api = environment.apiUrl;

  // ---- Evolutions ------------------------------------------------------

  listEvolutions(patientId: string): Observable<ClinicalEvolution[]> {
    return this.http.get<ClinicalEvolution[]>(`${this.api}/patients/${patientId}/evolutions`);
  }

  createEvolution(patientId: string, payload: EvolutionCreate): Observable<ClinicalEvolution> {
    return this.http.post<ClinicalEvolution>(`${this.api}/patients/${patientId}/evolutions`, payload);
  }

  // ---- Prescriptions ---------------------------------------------------

  listPrescriptions(patientId: string): Observable<Prescription[]> {
    return this.http.get<Prescription[]>(`${this.api}/patients/${patientId}/prescriptions`);
  }

  createPrescription(patientId: string, payload: PrescriptionCreate): Observable<Prescription> {
    return this.http.post<Prescription>(`${this.api}/patients/${patientId}/prescriptions`, payload);
  }

  // ---- Consents --------------------------------------------------------

  listConsentTemplates(): Observable<ConsentTemplate[]> {
    return this.http.get<ConsentTemplate[]>(`${this.api}/consents/templates`);
  }

  listConsents(patientId: string): Observable<Consent[]> {
    return this.http.get<Consent[]>(`${this.api}/patients/${patientId}/consents`);
  }

  createConsent(patientId: string, payload: ConsentCreate): Observable<Consent> {
    return this.http.post<Consent>(`${this.api}/patients/${patientId}/consents`, payload);
  }

  signConsent(consentId: string, payload: ConsentSignPayload): Observable<Consent> {
    return this.http.put<Consent>(`${this.api}/consents/${consentId}/sign`, payload);
  }

  /** Enlace para firmar a distancia; con sendEmail, además se envía al correo del paciente. */
  consentSignLink(consentId: string, sendEmail: boolean): Observable<ConsentSignLink> {
    return this.http.post<ConsentSignLink>(`${this.api}/consents/${consentId}/sign-link`, { send_email: sendEmail });
  }

  consentPdf(consentId: string): Observable<Blob> {
    return this.http.get(`${this.api}/consents/${consentId}/pdf`, { responseType: 'blob' });
  }

  consentLibrary(): Observable<ConsentLibraryItem[]> {
    return this.http.get<ConsentLibraryItem[]>(`${this.api}/consents/library`);
  }

  addConsentLibrary(names: string[] | null): Observable<{ added: number }> {
    return this.http.post<{ added: number }>(`${this.api}/consents/library`, { names });
  }

  publicConsent(token: string): Observable<PublicConsentView> {
    return this.http.get<PublicConsentView>(`${this.api}/public/consents/${token}`);
  }

  publicSign(
    token: string,
    body: { signed_by_name: string; signer_id_number: string | null; signer_relationship: string | null; signature_image: string; accept: boolean },
  ): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>(`${this.api}/public/consents/${token}/sign`, body);
  }

  // ---- Documents -------------------------------------------------------

  listDocuments(patientId: string, includeArchived = false): Observable<PatientDocument[]> {
    return this.http.get<PatientDocument[]>(`${this.api}/patients/${patientId}/documents`, {
      params: { include_archived: includeArchived },
    });
  }

  updateDocument(
    documentId: string,
    payload: { title: string; document_type: string; description: string | null },
  ): Observable<PatientDocument> {
    return this.http.put<PatientDocument>(`${this.api}/documents/${documentId}`, payload);
  }

  /** Un documento no se borra: se archiva con motivo y se puede restaurar. */
  archiveDocument(documentId: string, reason: string): Observable<PatientDocument> {
    return this.http.post<PatientDocument>(`${this.api}/documents/${documentId}/archive`, { reason });
  }

  restoreDocument(documentId: string): Observable<PatientDocument> {
    return this.http.post<PatientDocument>(`${this.api}/documents/${documentId}/restore`, {});
  }

  /** Anula un consentimiento pendiente o registra que el paciente revocó uno firmado. */
  voidConsent(consentId: string, reason: string): Observable<Consent> {
    return this.http.post<Consent>(`${this.api}/consents/${consentId}/void`, { reason });
  }

  uploadDocument(
    patientId: string,
    file: File,
    title: string,
    documentType: string,
    description?: string,
  ): Observable<PatientDocument> {
    const form = new FormData();
    form.append('file', file);
    form.append('title', title);
    form.append('document_type', documentType);
    if (description) form.append('description', description);
    return this.http.post<PatientDocument>(`${this.api}/patients/${patientId}/documents`, form);
  }

  downloadDocument(documentId: string): Observable<Blob> {
    return this.http.get(`${this.api}/documents/${documentId}/download`, { responseType: 'blob' });
  }

  /** Una receta no se borra: queda anulada, con su motivo, en la historia. */
  voidPrescription(patientId: string, prescriptionId: string, reason: string): Observable<Prescription> {
    return this.http.post<Prescription>(
      `${this.api}/patients/${patientId}/prescriptions/${prescriptionId}/void`,
      { reason },
    );
  }

  listAllConsentTemplates(): Observable<ConsentTemplate[]> {
    return this.http.get<ConsentTemplate[]>(`${this.api}/consents/templates`, {
      params: { include_inactive: true },
    });
  }

  createConsentTemplate(payload: Omit<ConsentTemplate, 'id' | 'is_active'>): Observable<ConsentTemplate> {
    return this.http.post<ConsentTemplate>(`${this.api}/consents/templates`, payload);
  }

  updateConsentTemplate(id: string, payload: Omit<ConsentTemplate, 'id'>): Observable<ConsentTemplate> {
    return this.http.put<ConsentTemplate>(`${this.api}/consents/templates/${id}`, payload);
  }

  /** Corrige una evolución; el servidor guarda el valor anterior en la auditoría. */
  voidEvolution(evolutionId: string, reason: string): Observable<ClinicalEvolution> {
    return this.http.post<ClinicalEvolution>(`${this.api}/evolutions/${evolutionId}/void`, { reason });
  }

  updateEvolution(evolutionId: string, payload: Partial<ClinicalEvolution>): Observable<ClinicalEvolution> {
    return this.http.put<ClinicalEvolution>(`${this.api}/evolutions/${evolutionId}`, payload);
  }
}
