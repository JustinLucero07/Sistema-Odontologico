import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  Branch,
  Clinic,
  Operatory,
  Professional,
  ProfessionalCreate,
  ProfessionalUpdate,
  Specialty,
} from '../models/clinic.models';

@Injectable({ providedIn: 'root' })
export class ClinicService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}`;

  getMyClinic(): Observable<Clinic> {
    return this.http.get<Clinic>(`${this.base}/clinics/me`);
  }

  updateMyClinic(payload: Partial<Clinic>): Observable<Clinic> {
    return this.http.put<Clinic>(`${this.base}/clinics/me`, payload);
  }

  listSpecialties(): Observable<Specialty[]> {
    return this.http.get<Specialty[]>(`${this.base}/specialties`);
  }

  createSpecialty(name: string): Observable<Specialty> {
    return this.http.post<Specialty>(`${this.base}/specialties`, { name });
  }

  listProfessionals(): Observable<Professional[]> {
    return this.http.get<Professional[]>(`${this.base}/professionals`);
  }

  createProfessional(payload: ProfessionalCreate): Observable<Professional> {
    return this.http.post<Professional>(`${this.base}/professionals`, payload);
  }

  updateProfessional(id: string, payload: ProfessionalUpdate): Observable<Professional> {
    return this.http.put<Professional>(`${this.base}/professionals/${id}`, payload);
  }

  updateSpecialty(id: string, name: string): Observable<Specialty> {
    return this.http.put<Specialty>(`${this.base}/specialties/${id}`, { name });
  }

  /** El servidor lo rechaza (409) si algún profesional la usa. */
  deleteSpecialty(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/specialties/${id}`);
  }

  // ---- Sedes y consultorios ------------------------------------------------

  listBranches(): Observable<Branch[]> {
    return this.http.get<Branch[]>(`${this.base}/clinics/branches`);
  }

  createBranch(payload: Partial<Branch>): Observable<Branch> {
    return this.http.post<Branch>(`${this.base}/clinics/branches`, payload);
  }

  updateBranch(id: string, payload: Partial<Branch>): Observable<Branch> {
    return this.http.put<Branch>(`${this.base}/clinics/branches/${id}`, payload);
  }

  deleteBranch(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/clinics/branches/${id}`);
  }

  listOperatories(): Observable<Operatory[]> {
    return this.http.get<Operatory[]>(`${this.base}/clinics/operatories`);
  }

  createOperatory(payload: { branch_id: string; name: string }): Observable<Operatory> {
    return this.http.post<Operatory>(`${this.base}/clinics/operatories`, payload);
  }

  updateOperatory(id: string, payload: Partial<Operatory>): Observable<Operatory> {
    return this.http.put<Operatory>(`${this.base}/clinics/operatories/${id}`, payload);
  }

  deleteOperatory(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/clinics/operatories/${id}`);
  }
}
