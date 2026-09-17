import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AuthService } from './auth.service';

/** Attaches the in-memory access token to every API request and, on a 401,
 * tries exactly one silent refresh (via the httpOnly refresh cookie) before
 * giving up and sending the user back to /login. */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  const isApiRequest = req.url.startsWith(environment.apiUrl);
  const isAuthEndpoint = req.url.includes('/auth/login') || req.url.includes('/auth/refresh');

  const token = auth.getAccessToken();
  const authorizedReq = isApiRequest && token && !isAuthEndpoint
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authorizedReq).pipe(
    catchError((error: unknown) => {
      if (
        error instanceof HttpErrorResponse &&
        error.status === 401 &&
        isApiRequest &&
        !isAuthEndpoint
      ) {
        return auth.refresh().pipe(
          switchMap(() => {
            const retried = req.clone({
              setHeaders: { Authorization: `Bearer ${auth.getAccessToken()}` },
            });
            return next(retried);
          }),
          catchError((refreshError: unknown) => {
            auth.setAccessToken(null);
            router.navigate(['/login']);
            return throwError(() => refreshError);
          }),
        );
      }
      return throwError(() => error);
    }),
  );
};
