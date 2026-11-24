import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  MedicalHistory,
  MedicalHistoryCreate,
  Patient,
  PatientCreate,
  PatientListItem,
  PatientUpdate,
  PatientImportPreview,
} from '../models/patient.models';

@Injectable({ providedIn: 'root' })
export class PatientsService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/patients`;

  listPatientsPage(search?: string): Observable<{ items: PatientListItem[]; total: number }> {
    let params = new HttpParams();
    if (search) params = params.set('search', search);
    return this.http
      .get<PatientListItem[]>(this.base, { params, observe: 'response' })
      .pipe(map((r) => ({ items: r.body ?? [], total: Number(r.headers.get('X-Total-Count') ?? r.body?.length ?? 0) })));
  }

  listPatients(search?: string): Observable<PatientListItem[]> {
    let params = new HttpParams();
    if (search) params = params.set('search', search);
    return this.http.get<PatientListItem[]>(this.base, { params });
  }

  getPatient(id: string): Observable<Patient> {
    return this.http.get<Patient>(`${this.base}/${id}`);
  }

  /** Lee un Excel/CSV y devuelve la vista previa, sin guardar nada. */
  importPreview(file: File, nameOrder: string, mapping?: Record<string, string | null>): Observable<PatientImportPreview> {
    const form = new FormData();
    form.append('file', file);
    form.append('name_order', nameOrder);
    if (mapping) form.append('mapping', JSON.stringify(mapping));
    return this.http.post<PatientImportPreview>(`${this.base}/import/preview`, form);
  }

  importConfirm(patients: PatientCreate[], skipDuplicates = true): Observable<{ created: number; skipped: number }> {
    return this.http.post<{ created: number; skipped: number }>(`${this.base}/import`, {
      patients,
      skip_duplicates: skipDuplicates,
    });
  }

  createPatient(payload: PatientCreate): Observable<Patient> {
    return this.http.post<Patient>(this.base, payload);
  }

  updatePatient(id: string, payload: PatientUpdate): Observable<Patient> {
    return this.http.put<Patient>(`${this.base}/${id}`, payload);
  }

  deactivatePatient(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }

  getLatestMedicalHistory(patientId: string): Observable<MedicalHistory | null> {
    return this.http.get<MedicalHistory | null>(`${this.base}/${patientId}/medical-history`);
  }

  listMedicalHistoryVersions(patientId: string): Observable<MedicalHistory[]> {
    return this.http.get<MedicalHistory[]>(`${this.base}/${patientId}/medical-history/versions`);
  }

  createMedicalHistoryVersion(
    patientId: string,
    payload: MedicalHistoryCreate,
  ): Observable<MedicalHistory> {
    return this.http.post<MedicalHistory>(`${this.base}/${patientId}/medical-history`, payload);
  }
}
