import { HttpClient } from '@angular/common/http';
import { Injectable, computed, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, finalize, firstValueFrom, shareReplay, tap } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AccessTokenResponse, CurrentUser, LoginRequest } from '../models/auth.models';

@Injectable({ providedIn: 'root' })
export class AuthService {
  // Access token lives in memory only (never localStorage) — the refresh
  // token is an httpOnly cookie the browser sends automatically, so a XSS
  // payload that reads JS-accessible storage can't steal a long-lived credential.
  private accessToken: string | null = null;

  private readonly currentUserSignal = signal<CurrentUser | null>(null);
  readonly currentUser = this.currentUserSignal.asReadonly();
  readonly isAuthenticated = computed(() => this.currentUserSignal() !== null);

  constructor(
    private readonly http: HttpClient,
    private readonly router: Router,
  ) {}

  getAccessToken(): string | null {
    return this.accessToken;
  }

  setAccessToken(token: string | null): void {
    this.accessToken = token;
  }

  login(payload: LoginRequest): Observable<AccessTokenResponse> {
    return this.http
      .post<AccessTokenResponse>(`${environment.apiUrl}/auth/login`, payload, { withCredentials: true })
      .pipe(tap((response) => (this.accessToken = response.access_token)));
  }

  /** Renovación en curso, compartida. Cuando el pase de acceso vence, el panel
   *  lanza varias peticiones a la vez y todas reciben 401: si cada una renovaba
   *  por su cuenta, la primera invalidaba el token de las demás y la sesión se
   *  cerraba. Ahora todas esperan la misma renovación. */
  private refreshInFlight: Observable<AccessTokenResponse> | null = null;

  refresh(): Observable<AccessTokenResponse> {
    this.refreshInFlight ??= this.http
      .post<AccessTokenResponse>(`${environment.apiUrl}/auth/refresh`, {}, { withCredentials: true })
      .pipe(
        tap((response) => (this.accessToken = response.access_token)),
        finalize(() => (this.refreshInFlight = null)),
        shareReplay(1),
      );
    return this.refreshInFlight;
  }

  async loadCurrentUser(): Promise<CurrentUser | null> {
    try {
      const user = await firstValueFrom(this.http.get<CurrentUser>(`${environment.apiUrl}/auth/me`));
      this.currentUserSignal.set(user);
      return user;
    } catch {
      this.currentUserSignal.set(null);
      return null;
    }
  }

  async logout(): Promise<void> {
    try {
      await firstValueFrom(this.http.post(`${environment.apiUrl}/auth/logout`, {}, { withCredentials: true }));
    } finally {
      this.accessToken = null;
      this.currentUserSignal.set(null);
      await this.router.navigate(['/login']);
    }
  }

  hasPermission(code: string): boolean {
    const user = this.currentUserSignal();
    if (!user) return false;
    return user.is_superadmin || user.permissions.includes(code);
  }
}
