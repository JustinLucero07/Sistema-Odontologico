import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';

export interface MailSettings {
  configured: boolean;
  source: 'consulta' | 'servidor' | 'ninguno';
  host: string | null;
  port: number;
  security: 'starttls' | 'ssl' | 'none';
  username: string | null;
  has_password: boolean;
  from_email: string | null;
  from_name: string | null;
  reminders_enabled: boolean;
  last_test_at: string | null;
  last_test_ok: boolean | null;
  last_error: string | null;
}

export interface MailProvider {
  code: string;
  label: string;
  host: string;
  port: number;
  security: 'starttls' | 'ssl' | 'none';
  help: string;
}

@Injectable({ providedIn: 'root' })
export class MailService {
  private readonly http = inject(HttpClient);
  private readonly api = `${environment.apiUrl}/mail`;

  providers(): Observable<MailProvider[]> {
    return this.http.get<MailProvider[]>(`${this.api}/providers`);
  }

  settings(): Observable<MailSettings> {
    return this.http.get<MailSettings>(`${this.api}/settings`);
  }

  save(body: Partial<MailSettings> & { password?: string | null }): Observable<MailSettings> {
    return this.http.put<MailSettings>(`${this.api}/settings`, body);
  }

  clear(): Observable<MailSettings> {
    return this.http.delete<MailSettings>(`${this.api}/settings`);
  }

  test(to: string): Observable<MailSettings> {
    return this.http.post<MailSettings>(`${this.api}/test`, { to });
  }
}
