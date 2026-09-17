import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatMenuModule } from '@angular/material/menu';
import { MatButtonModule } from '@angular/material/button';

import { AuthService } from '../../core/auth/auth.service';
import { HasPermissionDirective } from '../../core/auth/has-permission.directive';

interface NavItem {
  label: string;
  icon: string;
  route: string;
  permission?: string;
}

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [
    RouterLink,
    RouterLinkActive,
    RouterOutlet,
    MatIconModule,
    MatListModule,
    MatSidenavModule,
    MatToolbarModule,
    MatMenuModule,
    MatButtonModule,
    HasPermissionDirective,
  ],
  templateUrl: './shell.component.html',
  styleUrl: './shell.component.scss',
})
export class ShellComponent {
  readonly auth = inject(AuthService);

  readonly navItems: NavItem[] = [
    { label: 'Panel principal', icon: 'space_dashboard', route: '/dashboard' },
    { label: 'Pacientes', icon: 'groups', route: '/patients', permission: 'patients:read' },
    { label: 'Usuarios', icon: 'group', route: '/settings/users', permission: 'users:manage' },
    { label: 'Roles y permisos', icon: 'admin_panel_settings', route: '/settings/roles', permission: 'roles:manage' },
    { label: 'Profesionales', icon: 'medical_information', route: '/settings/professionals', permission: 'settings:manage' },
    { label: 'Clínica', icon: 'storefront', route: '/settings/clinic', permission: 'settings:manage' },
  ];

  async logout(): Promise<void> {
    await this.auth.logout();
  }
}
