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

  signConsent(consentId: string, signedByName: string, notes?: string): Observable<Consent> {
    return this.http.put<Consent>(`${this.api}/consents/${consentId}/sign`, {
      signed_by_name: signedByName,
      signature_notes: notes ?? null,
    });
  }

  // ---- Documents -------------------------------------------------------

  listDocuments(patientId: string): Observable<PatientDocument[]> {
    return this.http.get<PatientDocument[]>(`${this.api}/patients/${patientId}/documents`);
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
}
