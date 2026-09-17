import { Directive, Input, TemplateRef, ViewContainerRef, effect, inject } from '@angular/core';

import { AuthService } from './auth.service';

/** Structural directive to hide UI the user can't act on:
 * `<button *appHasPermission="'patients:write'">Nuevo paciente</button>`
 * Cosmetic only — the backend enforces the real permission check. */
@Directive({
  selector: '[appHasPermission]',
  standalone: true,
})
export class HasPermissionDirective {
  private readonly templateRef = inject(TemplateRef<unknown>);
  private readonly viewContainer = inject(ViewContainerRef);
  private readonly auth = inject(AuthService);

  private permission = '';
  private hasView = false;

  @Input() set appHasPermission(code: string) {
    this.permission = code;
  }

  constructor() {
    effect(() => {
      // Reading auth.currentUser() here makes this effect re-run whenever the
      // user (and therefore their permission set) changes.
      this.auth.currentUser();
      const allowed = this.auth.hasPermission(this.permission);

      if (allowed && !this.hasView) {
        this.viewContainer.createEmbeddedView(this.templateRef);
        this.hasView = true;
      } else if (!allowed && this.hasView) {
        this.viewContainer.clear();
        this.hasView = false;
      }
    });
  }
}
