import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ClinicalImage, ClinicalImageTypeOption } from '../models/clinical-image.models';

export interface ImageUpload {
  file: File;
  title: string;
  image_type: string;
  description?: string | null;
  taken_on?: string | null;
  /** Comma-separated FDI numbers, e.g. "16,17" for a bitewing. */
  fdi_numbers?: string | null;
}

@Injectable({ providedIn: 'root' })
export class ImagingService {
  private readonly http = inject(HttpClient);

  getTypes(): Observable<ClinicalImageTypeOption[]> {
    return this.http.get<ClinicalImageTypeOption[]>(`${environment.apiUrl}/images/types`);
  }

  list(patientId: string, includeArchived = false): Observable<ClinicalImage[]> {
    const query = includeArchived ? '?include_archived=true' : '';
    return this.http.get<ClinicalImage[]>(
      `${environment.apiUrl}/patients/${patientId}/images${query}`,
    );
  }

  upload(patientId: string, payload: ImageUpload): Observable<ClinicalImage> {
    const form = new FormData();
    form.append('file', payload.file);
    form.append('title', payload.title);
    form.append('image_type', payload.image_type);
    if (payload.description) form.append('description', payload.description);
    if (payload.taken_on) form.append('taken_on', payload.taken_on);
    if (payload.fdi_numbers) form.append('fdi_numbers', payload.fdi_numbers);
    return this.http.post<ClinicalImage>(
      `${environment.apiUrl}/patients/${patientId}/images`,
      form,
    );
  }

  /** The viewer loads bytes through the API so the auth interceptor applies —
   *  a clinical image is never a public URL. */
  fetchBlob(imageId: string): Observable<Blob> {
    return this.http.get(`${environment.apiUrl}/images/${imageId}/file`, {
      responseType: 'blob',
    });
  }

  /** There is no delete. A withdrawn study stays in the record with its
   *  reason, because "which image was seen at the time" is itself clinical. */
  archive(imageId: string, reason: string): Observable<ClinicalImage> {
    return this.http.post<ClinicalImage>(`${environment.apiUrl}/images/${imageId}/archive`, {
      reason,
    });
  }
}
