import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Clinic, Professional, ProfessionalCreate, Specialty } from '../models/clinic.models';

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
}
