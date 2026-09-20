import { Routes } from '@angular/router';

import { authGuard } from './core/auth/auth.guard';
import { permissionGuard } from './core/auth/permission.guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./features/auth/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'portal/:token',
    loadComponent: () =>
      import('./features/portal/portal-page.component').then((m) => m.PortalPageComponent),
  },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./layout/shell/shell.component').then((m) => m.ShellComponent),
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
      },
      {
        path: 'patients',
        canActivate: [permissionGuard],
        data: { permission: 'patients:read' },
        loadComponent: () =>
          import('./features/patients/patients-list/patients-list.component').then(
            (m) => m.PatientsListComponent,
          ),
      },
      {
        path: 'patients/:id',
        canActivate: [permissionGuard],
        data: { permission: 'patients:read' },
        loadComponent: () =>
          import('./features/patients/patient-detail/patient-detail.component').then(
            (m) => m.PatientDetailComponent,
          ),
      },
      {
        path: 'odontogram',
        canActivate: [permissionGuard],
        data: { permission: 'odontogram:read' },
        loadComponent: () =>
          import('./features/odontogram/odontogram-search/odontogram-search.component').then(
            (m) => m.OdontogramSearchComponent,
          ),
      },
      {
        path: 'settings/users',
        canActivate: [permissionGuard],
        data: { permission: 'users:manage' },
        loadComponent: () =>
          import('./features/settings/users/users.component').then((m) => m.UsersComponent),
      },
      {
        path: 'settings/roles',
        canActivate: [permissionGuard],
        data: { permission: 'roles:manage' },
        loadComponent: () =>
          import('./features/settings/roles/roles.component').then((m) => m.RolesComponent),
      },
      {
        path: 'agenda',
        canActivate: [permissionGuard],
        data: { permission: 'appointments:read' },
        loadComponent: () =>
          import('./features/agenda/agenda.component').then((m) => m.AgendaComponent),
      },
      {
        path: 'treatment-plans',
        canActivate: [permissionGuard],
        data: { permission: 'treatments:read' },
        loadComponent: () =>
          import('./features/treatment-plans/treatment-plans-page.component').then(
            (m) => m.TreatmentPlansPageComponent,
          ),
      },
      {
        path: 'budgets',
        canActivate: [permissionGuard],
        data: { permission: 'budgets:read' },
        loadComponent: () =>
          import('./features/budgets/budgets-page.component').then((m) => m.BudgetsPageComponent),
      },
      {
        path: 'cash',
        canActivate: [permissionGuard],
        data: { permission: 'payments:read' },
        loadComponent: () =>
          import('./features/finance/cash-page.component').then((m) => m.CashPageComponent),
      },
      {
        path: 'inventory',
        canActivate: [permissionGuard],
        data: { permission: 'inventory:read' },
        loadComponent: () =>
          import('./features/inventory/inventory-page.component').then((m) => m.InventoryPageComponent),
      },
      {
        path: 'laboratory',
        canActivate: [permissionGuard],
        data: { permission: 'laboratory:read' },
        loadComponent: () =>
          import('./features/laboratory/laboratory-page.component').then((m) => m.LaboratoryPageComponent),
      },
      {
        path: 'reports',
        canActivate: [permissionGuard],
        data: { permission: 'reports:read' },
        loadComponent: () =>
          import('./features/reports/reports-page.component').then((m) => m.ReportsPageComponent),
      },
      {
        path: 'settings/treatments',
        canActivate: [permissionGuard],
        data: { permission: 'treatments:write' },
        loadComponent: () =>
          import('./features/settings/treatments/treatments.component').then((m) => m.TreatmentsComponent),
      },
      {
        path: 'settings/professionals',
        canActivate: [permissionGuard],
        data: { permission: 'settings:manage' },
        loadComponent: () =>
          import('./features/settings/professionals/professionals.component').then(
            (m) => m.ProfessionalsComponent,
          ),
      },
      {
        path: 'settings/clinic',
        canActivate: [permissionGuard],
        data: { permission: 'settings:manage' },
        loadComponent: () =>
          import('./features/settings/clinic/clinic.component').then((m) => m.ClinicComponent),
      },
    ],
  },
  { path: '**', redirectTo: 'dashboard' },
];
