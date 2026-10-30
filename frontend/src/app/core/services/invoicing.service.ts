import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  Invoice,
  InvoiceCreate,
  InvoiceableCharge,
  InvoicingCatalogs,
  InvoicingSettings,
} from '../models/invoicing.models';

export interface InvoiceFilters {
  status?: string | null;
  doc_type?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  q?: string | null;
}

@Injectable({ providedIn: 'root' })
export class InvoicingService {
  private readonly http = inject(HttpClient);
  private readonly api = environment.apiUrl;

  catalogs(): Observable<InvoicingCatalogs> {
    return this.http.get<InvoicingCatalogs>(`${this.api}/invoicing/catalogs`);
  }

  settings(): Observable<InvoicingSettings> {
    return this.http.get<InvoicingSettings>(`${this.api}/invoicing/settings`);
  }

  saveSettings(body: Partial<InvoicingSettings> & { next_invoice_number?: number }): Observable<InvoicingSettings> {
    return this.http.put<InvoicingSettings>(`${this.api}/invoicing/settings`, body);
  }

  uploadCertificate(file: File, password: string): Observable<InvoicingSettings> {
    const form = new FormData();
    form.append('file', file);
    form.append('password', password);
    return this.http.post<InvoicingSettings>(`${this.api}/invoicing/certificate`, form);
  }

  deleteCertificate(): Observable<InvoicingSettings> {
    return this.http.delete<InvoicingSettings>(`${this.api}/invoicing/certificate`);
  }

  list(filters: InvoiceFilters = {}): Observable<Invoice[]> {
    let params = new HttpParams();
    for (const [k, v] of Object.entries(filters)) if (v) params = params.set(k, v);
    return this.http.get<Invoice[]>(`${this.api}/invoices`, { params });
  }

  forPatient(patientId: string): Observable<Invoice[]> {
    return this.http.get<Invoice[]>(`${this.api}/patients/${patientId}/invoices`);
  }

  invoiceableCharges(patientId: string): Observable<InvoiceableCharge[]> {
    return this.http.get<InvoiceableCharge[]>(`${this.api}/patients/${patientId}/invoiceable-charges`);
  }

  get(id: string): Observable<Invoice> {
    return this.http.get<Invoice>(`${this.api}/invoices/${id}`);
  }

  create(body: InvoiceCreate): Observable<Invoice> {
    return this.http.post<Invoice>(`${this.api}/invoices`, body);
  }

  retry(id: string): Observable<Invoice> {
    return this.http.post<Invoice>(`${this.api}/invoices/${id}/retry`, {});
  }

  discard(id: string, reason: string): Observable<Invoice> {
    return this.http.post<Invoice>(`${this.api}/invoices/${id}/discard`, { reason });
  }

  creditNote(id: string, reason: string, amount: string | null): Observable<Invoice> {
    return this.http.post<Invoice>(`${this.api}/invoices/${id}/credit-note`, { reason, amount });
  }

  email(id: string, email: string | null): Observable<Invoice> {
    return this.http.post<Invoice>(`${this.api}/invoices/${id}/email`, { email });
  }

  pdf(id: string): Observable<Blob> {
    return this.http.get(`${this.api}/invoices/${id}/pdf`, { responseType: 'blob' });
  }

  xml(id: string): Observable<Blob> {
    return this.http.get(`${this.api}/invoices/${id}/xml`, { responseType: 'blob' });
  }
}
