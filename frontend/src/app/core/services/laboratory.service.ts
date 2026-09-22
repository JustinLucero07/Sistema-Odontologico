import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { LabCatalog, LabOrder, Laboratory } from '../models/laboratory.models';

export interface LabOrderInput {
  patient_id: string;
  laboratory_id: string;
  work_type: string;
  description: string;
  professional_id?: string | null;
  fdi_numbers?: string[];
  shade?: string | null;
  material?: string | null;
  due_on?: string | null;
  cost?: string | null;
  notes?: string | null;
}

/** Lo que se puede corregir de un trabajo abierto: todo menos paciente y estado. */
export type LabOrderEdit = Omit<LabOrderInput, 'patient_id' | 'professional_id'>;

@Injectable({ providedIn: 'root' })
export class LaboratoryService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/laboratory`;

  getCatalog(): Observable<LabCatalog> {
    return this.http.get<LabCatalog>(`${this.base}/catalog`);
  }

  listLaboratories(): Observable<Laboratory[]> {
    return this.http.get<Laboratory[]>(`${this.base}/laboratories`);
  }

  createLaboratory(body: Partial<Laboratory>): Observable<Laboratory> {
    return this.http.post<Laboratory>(`${this.base}/laboratories`, body);
  }

  listOrders(options: { patientId?: string; openOnly?: boolean } = {}): Observable<LabOrder[]> {
    const params = new URLSearchParams();
    if (options.patientId) params.set('patient_id', options.patientId);
    if (options.openOnly) params.set('open_only', 'true');
    const query = params.toString() ? `?${params}` : '';
    return this.http.get<LabOrder[]>(`${this.base}/orders${query}`);
  }

  createOrder(body: LabOrderInput): Observable<LabOrder> {
    return this.http.post<LabOrder>(`${this.base}/orders`, body);
  }

  /** A case only moves forward; the server refuses anything else. */
  updateStatus(orderId: string, status: string, note?: string | null): Observable<LabOrder> {
    return this.http.put<LabOrder>(`${this.base}/orders/${orderId}/status`, {
      status,
      note: note ?? null,
    });
  }

  updateLaboratory(laboratoryId: string, body: Partial<Laboratory>): Observable<Laboratory> {
    return this.http.put<Laboratory>(`${this.base}/laboratories/${laboratoryId}`, body);
  }

  updateOrder(orderId: string, body: LabOrderEdit): Observable<LabOrder> {
    return this.http.put<LabOrder>(`${this.base}/orders/${orderId}`, body);
  }
}
