import { Component, HostListener, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatMenuModule } from '@angular/material/menu';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, debounceTime, distinctUntilChanged, firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { HasPermissionDirective } from '../../core/auth/has-permission.directive';
import { PatientListItem } from '../../core/models/patient.models';
import { PatientsService } from '../../core/services/patients.service';
import { ThemeService } from '../../core/theme/theme.service';
import { ToothMarkComponent } from '../../shared/brand/tooth-mark.component';

interface NavItem {
  label: string;
  icon: string;
  route: string;
  permission?: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const COLLAPSED_KEY = 'odonto.sidenav.collapsed';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    RouterLinkActive,
    RouterOutlet,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatListModule,
    MatMenuModule,
    MatSidenavModule,
    MatToolbarModule,
    MatTooltipModule,
    HasPermissionDirective,
    ToothMarkComponent,
  ],
  templateUrl: './shell.component.html',
  styleUrl: './shell.component.scss',
})
export class ShellComponent {
  readonly auth = inject(AuthService);
  readonly theme = inject(ThemeService);
  private readonly patientsService = inject(PatientsService);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);

  readonly collapsed = signal(this.readCollapsed());

  readonly sections: NavSection[] = [
    {
      title: 'Clínica',
      items: [
        { label: 'Panel principal', icon: 'space_dashboard', route: '/dashboard' },
        { label: 'Pacientes', icon: 'groups', route: '/patients', permission: 'patients:read' },
        { label: 'Odontograma', icon: 'healing', route: '/odontogram', permission: 'odontogram:read' },
        { label: 'Agenda', icon: 'event', route: '/agenda', permission: 'appointments:read' },
      ],
    },
    {
      title: 'Gestión',
      items: [
        {
          label: 'Planes de tratamiento',
          icon: 'assignment',
          route: '/treatment-plans',
          permission: 'treatments:read',
        },
        { label: 'Presupuestos', icon: 'request_quote', route: '/budgets', permission: 'budgets:read' },
        {
          label: 'Catálogo de tratamientos',
          icon: 'medical_services',
          route: '/settings/treatments',
          permission: 'treatments:write',
        },
      ],
    },
    {
      title: 'Configuración',
      items: [
        { label: 'Usuarios', icon: 'group', route: '/settings/users', permission: 'users:manage' },
        {
          label: 'Roles y permisos',
          icon: 'admin_panel_settings',
          route: '/settings/roles',
          permission: 'roles:manage',
        },
        {
          label: 'Profesionales',
          icon: 'medical_information',
          route: '/settings/professionals',
          permission: 'settings:manage',
        },
        { label: 'Clínica', icon: 'storefront', route: '/settings/clinic', permission: 'settings:manage' },
      ],
    },
  ];

  // ---- Global search ----------------------------------------------------

  readonly searchControl = this.fb.nonNullable.control('');
  private readonly search$ = new Subject<string>();
  readonly searchResults = signal<PatientListItem[]>([]);
  readonly searchOpen = signal(false);

  constructor() {
    this.search$.pipe(debounceTime(250), distinctUntilChanged()).subscribe((term) => this.runSearch(term));
    this.searchControl.valueChanges.subscribe((value) => this.search$.next(value));
  }

  private async runSearch(term: string): Promise<void> {
    if (!term.trim() || !this.auth.hasPermission('patients:read')) {
      this.searchResults.set([]);
      return;
    }
    this.searchResults.set(await firstValueFrom(this.patientsService.listPatients(term)));
    this.searchOpen.set(true);
  }

  openPatient(patient: PatientListItem): void {
    this.closeSearch();
    this.router.navigate(['/patients', patient.id]);
  }

  closeSearch(): void {
    this.searchOpen.set(false);
    this.searchResults.set([]);
    this.searchControl.setValue('', { emitEvent: false });
  }

  @HostListener('document:keydown', ['$event'])
  handleShortcut(event: KeyboardEvent): void {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      document.getElementById('global-search')?.focus();
    }
    if (event.key === 'Escape') this.closeSearch();
  }

  // ---- Sidenav ----------------------------------------------------------

  toggleCollapsed(): void {
    const next = !this.collapsed();
    this.collapsed.set(next);
    try {
      localStorage.setItem(COLLAPSED_KEY, String(next));
    } catch {
      // Private browsing or blocked storage: the preference just won't persist.
    }
  }

  private readCollapsed(): boolean {
    try {
      return localStorage.getItem(COLLAPSED_KEY) === 'true';
    } catch {
      return false;
    }
  }

  visibleItems(section: NavSection): NavItem[] {
    return section.items.filter((item) => !item.permission || this.auth.hasPermission(item.permission));
  }

  themeIcon(): string {
    switch (this.theme.preference()) {
      case 'light':
        return 'light_mode';
      case 'dark':
        return 'dark_mode';
      default:
        return 'contrast';
    }
  }

  themeLabel(): string {
    switch (this.theme.preference()) {
      case 'light':
        return 'Modo claro';
      case 'dark':
        return 'Modo oscuro';
      default:
        return 'Según el sistema';
    }
  }

  async logout(): Promise<void> {
    await this.auth.logout();
  }
}
