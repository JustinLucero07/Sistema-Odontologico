import { BreakpointObserver } from '@angular/cdk/layout';
import { Component, DestroyRef, HostListener, computed, effect, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatMenuModule } from '@angular/material/menu';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, debounceTime, distinctUntilChanged, firstValueFrom, map } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { BrandingService } from '../../core/branding/branding.service';
import { HasPermissionDirective } from '../../core/auth/has-permission.directive';
import { PatientListItem } from '../../core/models/patient.models';
import { PatientsService } from '../../core/services/patients.service';
import { ThemeService } from '../../core/theme/theme.service';
import { ToothMarkComponent } from '../../shared/brand/tooth-mark.component';
import { openPatientCreateDialog } from '../../shared/patient-dialog/patient-create-dialog.component';
import { ConfidentialityDialogComponent } from '../../shared/legal/confidentiality-dialog.component';
import { openChangePassword } from '../../shared/legal/change-password-dialog.component';

interface NavItem {
  label: string;
  icon: string;
  route: string;
  permission?: string;
  /** Módulo opcional: la consulta puede ocultarlo en Personalización. */
  module?: string;
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
  private readonly dialog = inject(MatDialog);
  private readonly snack = inject(MatSnackBar);

  readonly collapsed = signal(this.readCollapsed());

  /** Pantallas estrechas (tablet vertical, móvil): el menú flota sobre el
   *  contenido y se abre con un botón, en vez de ocupar un tercio del ancho. */
  readonly compact = toSignal(
    inject(BreakpointObserver)
      .observe('(max-width: 960px)')
      .pipe(map((state) => state.matches)),
    { initialValue: false },
  );

  // Tres grupos por lo que se hace en cada uno: atender, administrar,
  // configurar. Odontograma, planes y presupuestos no están aquí porque son de
  // UN paciente y viven como pestañas en su ficha; como entradas sueltas solo
  // eran un buscador que llevaba allí.
  readonly sections: NavSection[] = [
    {
      title: 'Clínica',
      items: [
        { label: 'Panel principal', icon: 'space_dashboard', route: '/dashboard' },
        { label: 'Agenda', icon: 'event', route: '/agenda', permission: 'appointments:read' },
        { label: 'Pacientes', icon: 'groups', route: '/patients', permission: 'patients:read' },
        { label: 'Oportunidades', icon: 'tips_and_updates', route: '/opportunities', permission: 'patients:read', module: 'opportunities' },
      ],
    },
    {
      title: 'Administración',
      items: [
        { label: 'Caja del día', icon: 'point_of_sale', route: '/cash', permission: 'payments:read', module: 'cash' },
        { label: 'Finanzas', icon: 'account_balance', route: '/finance', permission: 'payments:read' },
        { label: 'Facturación', icon: 'receipt_long', route: '/invoices', permission: 'invoices:read' },
        { label: 'Cartera', icon: 'account_balance_wallet', route: '/portfolio', permission: 'payments:read' },
        { label: 'Créditos', icon: 'credit_score', route: '/credits', permission: 'payments:read', module: 'credits' },
        { label: 'Reportes', icon: 'insights', route: '/reports', permission: 'reports:read', module: 'reports' },
        { label: 'Inventario', icon: 'inventory_2', route: '/inventory', permission: 'inventory:read', module: 'inventory' },
        {
          label: 'Laboratorio',
          icon: 'precision_manufacturing',
          route: '/laboratory',
          permission: 'laboratory:read',
          module: 'laboratory',
        },
      ],
    },
    {
      title: 'Configuración',
      items: [
        {
          label: 'Tratamientos',
          icon: 'medical_services',
          route: '/settings/treatments',
          permission: 'treatments:write',
        },
        {
          label: 'Consentimientos',
          icon: 'draw',
          route: '/settings/consents',
          permission: 'consents:write',
          module: 'consents',
        },
        {
          label: 'Mensajes',
          icon: 'forum',
          route: '/settings/messages',
          permission: 'settings:manage',
          module: 'messages',
        },
        {
          label: 'Profesionales',
          icon: 'medical_information',
          route: '/settings/professionals',
          permission: 'settings:manage',
        },
        { label: 'Usuarios', icon: 'group', route: '/settings/users', permission: 'users:manage' },
        {
          label: 'Roles y permisos',
          icon: 'admin_panel_settings',
          route: '/settings/roles',
          permission: 'roles:manage',
        },
        { label: 'Personalización', icon: 'palette', route: '/settings/branding', permission: 'settings:manage' },
        { label: 'Legal y cumplimiento', icon: 'gavel', route: '/settings/compliance', permission: 'settings:manage' },
        { label: 'Datos de la consulta', icon: 'storefront', route: '/settings/clinic', permission: 'settings:manage' },
      ],
    },
  ];

  // ---- Global search ----------------------------------------------------

  readonly searchControl = this.fb.nonNullable.control('');
  private readonly search$ = new Subject<string>();
  readonly searchResults = signal<PatientListItem[]>([]);
  readonly searchOpen = signal(false);

  readonly branding = inject(BrandingService);
  private confidentialityOpen = false;

  /** Avisos de cumplimiento para el administrador, arriba de cada página. */
  readonly avisosLegales = computed(() => {
    const b = this.branding.branding();
    if (!b || !b.setup_completed || !this.auth.hasPermission('settings:manage')) return [];
    const avisos: { icon: string; text: string; tone: 'warn' | 'danger' }[] = [];
    if (b.terms_pending) {
      avisos.push({ icon: 'gavel', tone: 'warn', text: 'Hay una nueva versión de los Términos de uso. Revísala y acéptala.' });
    }
    if (b.health_permit_expires_on) {
      const dias = Math.round((new Date(b.health_permit_expires_on + 'T12:00').getTime() - Date.now()) / 86_400_000);
      if (dias < 0) avisos.push({ icon: 'error', tone: 'danger', text: `El permiso de funcionamiento venció hace ${-dias} días.` });
      else if (dias <= 30) avisos.push({ icon: 'event_busy', tone: 'warn', text: `El permiso de funcionamiento vence en ${dias} días.` });
    }
    return avisos;
  });

  // ---- Cierre de sesión por inactividad --------------------------------
  // La última actividad se comparte entre pestañas: trabajar en una mantiene
  // abiertas las demás.
  private static readonly ACTIVIDAD = 'odonto.lastActivity';
  private ultimaMarca = 0;

  @HostListener('document:pointerdown')
  @HostListener('document:keydown.capture')
  @HostListener('document:wheel')
  @HostListener('document:touchstart')
  registrarActividad(): void {
    const ahora = Date.now();
    if (ahora - this.ultimaMarca < 15_000) return;
    this.ultimaMarca = ahora;
    try {
      localStorage.setItem(ShellComponent.ACTIVIDAD, String(ahora));
    } catch {
      // Sin almacenamiento cuenta solo esta pestaña.
    }
  }

  private ultimaActividad(): number {
    try {
      return Math.max(this.ultimaMarca, Number(localStorage.getItem(ShellComponent.ACTIVIDAD) ?? 0));
    } catch {
      return this.ultimaMarca;
    }
  }

  private vigilarInactividad(): void {
    this.registrarActividad();
    const id = setInterval(() => {
      const minutos = this.branding.branding()?.session_timeout_minutes ?? 0;
      if (!minutos || !this.auth.currentUser()) return;
      if (Date.now() - this.ultimaActividad() > minutos * 60_000) {
        clearInterval(id);
        void this.auth.logout().then(() =>
          this.snack.open('Se cerró la sesión por inactividad, para proteger los datos de los pacientes.', 'Cerrar', {
            duration: 8000,
          }),
        );
      }
    }, 20_000);
    inject(DestroyRef).onDestroy(() => clearInterval(id));
  }
  private passwordOpen = false;

  constructor() {
    // Nadie trabaja con datos de pacientes sin haber aceptado el acuerdo
    // vigente: si falta, se pide antes de cualquier otra cosa.
    effect(() => {
      const user = this.auth.currentUser();
      // Primero la contraseña temporal; el acuerdo viene después.
      if (user?.must_change_password) {
        if (!this.passwordOpen) {
          this.passwordOpen = true;
          void openChangePassword(this.dialog, true).finally(() => (this.passwordOpen = false));
        }
        return;
      }
      // Primer ingreso del administrador: el asistente de bienvenida.
      const marca = this.branding.branding();
      if (
        user &&
        !user.confidentiality_required &&
        marca &&
        !marca.setup_completed &&
        this.auth.hasPermission('settings:manage')
      ) {
        void this.router.navigate(['/setup']);
        return;
      }
      if (user?.confidentiality_required && !this.confidentialityOpen) {
        this.confidentialityOpen = true;
        this.dialog
          .open(ConfidentialityDialogComponent, {
            width: '680px',
            maxWidth: '96vw',
            disableClose: true,
            panelClass: 'app-dialog',
          })
          .afterClosed()
          .subscribe(() => (this.confidentialityOpen = false));
      }
    });

    void this.branding.load();
    this.vigilarInactividad();
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
    const ocultos = this.branding.hidden();
    return section.items.filter(
      (item) =>
        (!item.permission || this.auth.hasPermission(item.permission)) && !(item.module && ocultos.has(item.module)),
    );
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

  // ---- Crear desde cualquier pantalla ---------------------------------------

  async newPatient(): Promise<void> {
    const created = await openPatientCreateDialog(this.dialog);
    if (created) this.router.navigate(['/patients', created.id]);
  }

  newAppointment(): void {
    this.router.navigate(['/agenda'], { queryParams: { nueva: 1 } });
  }

  async changePassword(): Promise<void> {
    if (await openChangePassword(this.dialog)) {
      this.snack.open('Contraseña actualizada. Las demás sesiones se cerraron.', 'Cerrar', { duration: 4000 });
    }
  }

  async logout(): Promise<void> {
    await this.auth.logout();
  }
}
