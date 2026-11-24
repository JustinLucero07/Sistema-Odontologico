import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isAuthenticated()) {
    return true;
  }

  try {
    await firstValueFrom(auth.refresh());
    const user = await auth.loadCurrentUser();
    if (user) return true;
  } catch {
    // fall through to redirect
  }

  return router.createUrlTree(['/login']);
};
