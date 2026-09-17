import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth.service';

/** Route-level RBAC check: `data: { permission: 'users:manage' }` on a route.
 * The backend is the real authority (every endpoint re-checks permissions);
 * this only avoids flashing a screen the user can't act on. */
export const permissionGuard: CanActivateFn = (route) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const required = route.data['permission'] as string | undefined;

  if (!required || auth.hasPermission(required)) {
    return true;
  }
  return router.createUrlTree(['/dashboard']);
};
