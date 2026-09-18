import { Component, OnInit, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { PatientsService } from '../../core/services/patients.service';
import { TreatmentsService } from '../../core/services/treatments.service';

interface QuickLink {
  label: string;
  description: string;
  icon: string;
  route: string;
  permission: string;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [MatCardModule, MatIconModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
  readonly auth = inject(AuthService);
  private readonly patientsService = inject(PatientsService);
  private readonly treatmentsService = inject(TreatmentsService);
  private readonly router = inject(Router);

  readonly patientCount = signal<number | null>(null);
  readonly treatmentCount = signal<number | null>(null);

  readonly quickLinks: QuickLink[] = [
    {
      label: 'Pacientes',
      description: 'Buscar, registrar y abrir la ficha de un paciente',
      icon: 'groups',
      route: '/patients',
      permission: 'patients:read',
    },
    {
      label: 'Odontograma',
      description: 'Buscar un paciente y abrir su odontograma directamente',
      icon: 'healing',
      route: '/odontogram',
      permission: 'odontogram:read',
    },
    {
      label: 'Catálogo de tratamientos',
      description: 'Precios y procedimientos que ofrece la clínica',
      icon: 'medical_services',
      route: '/settings/treatments',
      permission: 'treatments:write',
    },
    {
      label: 'Usuarios y roles',
      description: 'Administrar el equipo y sus permisos',
      icon: 'group',
      route: '/settings/users',
      permission: 'users:manage',
    },
  ];

  get visibleQuickLinks(): QuickLink[] {
    return this.quickLinks.filter((link) => this.auth.hasPermission(link.permission));
  }

  async ngOnInit(): Promise<void> {
    if (this.auth.hasPermission('patients:read')) {
      try {
        const patients = await firstValueFrom(this.patientsService.listPatients());
        this.patientCount.set(patients.length);
      } catch {
        this.patientCount.set(null);
      }
    }
    if (this.auth.hasPermission('treatments:read')) {
      try {
        const treatments = await firstValueFrom(this.treatmentsService.list());
        this.treatmentCount.set(treatments.length);
      } catch {
        this.treatmentCount.set(null);
      }
    }
  }

  goTo(route: string): void {
    this.router.navigate([route]);
  }
}
