import { DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';
import { formatMoney } from '../../core/models/finance.models';
import { SkeletonComponent } from '../../shared/skeleton/skeleton.component';
import { whatsappUrl } from '../../shared/whatsapp';

interface PatientBalance {
  patient_id: string; patient_name: string; national_id: string | null; phone: string | null;
  total_charged: string; total_paid: string; balance: string; status: 'debe' | 'saldado' | 'a_favor';
  open_charges: number; oldest_pending_on: string | null; days_pending: number | null; last_payment_on: string | null; in_credit: boolean;
}
interface ChargeRow {
  charge_id: string; patient_id: string; patient_name: string; description: string; issued_on: string;
  amount: string; paid: string; pending: string; status: 'pendiente' | 'parcial' | 'pagada'; in_credit: boolean; days_open: number;
}
interface TreatmentRow {
  item_id: string; patient_id: string; patient_name: string; plan_title: string; treatment: string; fdi_number: string | null;
  status: string; net_price: string; professional_name: string | null; estimated_date: string | null; completed_date: string | null;
}
interface Portfolio {
  summary: {
    total_charged: string; total_paid: string; receivable: string; credit_balance: string;
    patients_owing: number; patients_settled: number; patients_credit: number; open_charges: number;
    treatments_in_progress: number; treatments_in_progress_value: string; treatments_planned: number; treatments_planned_value: string;
    collection_rate: number | null;
  };
  patients: PatientBalance[]; charges: ChargeRow[]; treatments: TreatmentRow[];
}

type Vista = 'pacientes' | 'cargos' | 'tratamientos';

const ESTADO_TRAT: Record<string, string> = {
  propuesto: 'Propuesto', aprobado: 'Aprobado', en_progreso: 'En curso', completado: 'Terminado', cancelado: 'Cancelado', rechazado: 'Rechazado',
};

/**
 * Cartera: la foto de todo lo que se debe y de lo que está en curso, de todos
 * los pacientes a la vez, sin entrar ficha por ficha.
 */
@Component({
  selector: 'app-portfolio-page',
  standalone: true,
  imports: [DatePipe, FormsModule, MatButtonModule, MatIconModule, MatTooltipModule, RouterLink, SkeletonComponent],
  templateUrl: './portfolio-page.component.html',
  styleUrl: './portfolio-page.component.scss',
})
export class PortfolioPageComponent implements OnInit {
  private readonly http = inject(HttpClient);
  readonly money = formatMoney;
  readonly estadoTrat = ESTADO_TRAT;

  readonly data = signal<Portfolio | null>(null);
  readonly loading = signal(true);
  readonly vista = signal<Vista>('pacientes');
  readonly filtro = signal('debe');
  readonly buscar = signal('');

  readonly filtros = computed(() => {
    const d = this.data();
    if (!d) return [];
    const n = (f: (x: never) => boolean, l: unknown[]) => l.filter(f as never).length;
    switch (this.vista()) {
      case 'pacientes':
        return [
          { v: 'debe', l: 'Deben', c: d.summary.patients_owing },
          { v: 'saldado', l: 'Saldados', c: d.summary.patients_settled },
          { v: 'a_favor', l: 'Saldo a favor', c: d.summary.patients_credit },
          { v: 'todos', l: 'Todos', c: d.patients.length },
        ];
      case 'cargos':
        return [
          { v: 'abiertos', l: 'Por cobrar', c: n((c: ChargeRow) => c.status !== 'pagada', d.charges) },
          { v: 'parcial', l: 'Con abono', c: n((c: ChargeRow) => c.status === 'parcial', d.charges) },
          { v: 'pendiente', l: 'Sin abono', c: n((c: ChargeRow) => c.status === 'pendiente', d.charges) },
          { v: 'pagada', l: 'Pagados', c: n((c: ChargeRow) => c.status === 'pagada', d.charges) },
        ];
      default:
        return [
          { v: 'activos', l: 'Activos', c: n((t: TreatmentRow) => ['en_progreso', 'aprobado'].includes(t.status), d.treatments) },
          { v: 'en_progreso', l: 'En curso', c: n((t: TreatmentRow) => t.status === 'en_progreso', d.treatments) },
          { v: 'aprobado', l: 'Aprobados sin iniciar', c: n((t: TreatmentRow) => t.status === 'aprobado', d.treatments) },
          { v: 'propuesto', l: 'Propuestos', c: n((t: TreatmentRow) => t.status === 'propuesto', d.treatments) },
          { v: 'completado', l: 'Terminados', c: n((t: TreatmentRow) => t.status === 'completado', d.treatments) },
        ];
    }
  });

  private coincide(...textos: (string | null)[]): boolean {
    const q = this.buscar().trim().toLowerCase();
    return !q || textos.some((t) => (t ?? '').toLowerCase().includes(q));
  }

  readonly pacientes = computed(() =>
    (this.data()?.patients ?? []).filter(
      (p) => (this.filtro() === 'todos' || p.status === this.filtro()) && this.coincide(p.patient_name, p.national_id),
    ),
  );
  readonly cargos = computed(() =>
    (this.data()?.charges ?? []).filter((c) => {
      const f = this.filtro();
      const ok = f === 'abiertos' ? c.status !== 'pagada' : c.status === f;
      return ok && this.coincide(c.patient_name, c.description);
    }),
  );
  readonly tratamientos = computed(() =>
    (this.data()?.treatments ?? []).filter((t) => {
      const f = this.filtro();
      const ok = f === 'activos' ? ['en_progreso', 'aprobado'].includes(t.status) : t.status === f;
      return ok && this.coincide(t.patient_name, t.treatment, t.professional_name);
    }),
  );
  readonly totalVista = computed(() => {
    const sum = (l: string[]) => l.reduce((a, b) => a + Number(b), 0);
    switch (this.vista()) {
      case 'pacientes': return sum(this.pacientes().map((p) => p.balance));
      case 'cargos': return sum(this.cargos().map((c) => c.pending));
      default: return sum(this.tratamientos().map((t) => t.net_price));
    }
  });
  readonly cobranza = computed(() => Math.round((this.data()?.summary.collection_rate ?? 0) * 100));

  async ngOnInit(): Promise<void> {
    await this.cargar();
  }

  async cargar(): Promise<void> {
    this.loading.set(true);
    try {
      this.data.set(await firstValueFrom(this.http.get<Portfolio>(`${environment.apiUrl}/finance/portfolio`)));
    } finally {
      this.loading.set(false);
    }
  }

  cambiarVista(v: Vista): void {
    this.vista.set(v);
    this.filtro.set(v === 'pacientes' ? 'debe' : v === 'cargos' ? 'abiertos' : 'activos');
  }

  wa(p: PatientBalance): string | null {
    const nombre = p.patient_name.split(' ')[0];
    return whatsappUrl(p.phone, `Hola ${nombre}, le recordamos que tiene un saldo pendiente de $ ${formatMoney(p.balance)}. ¡Gracias!`);
  }

  /** Exporta la vista actual a CSV (se abre en Excel). */
  exportar(): void {
    const filas: (string | number)[][] = [];
    const n = (v: string | number) => String(v).replace('.', ',');
    if (this.vista() === 'pacientes') {
      filas.push(['Paciente', 'Cédula', 'Teléfono', 'Total cargado', 'Total pagado', 'Saldo', 'Estado', 'Cargos abiertos', 'Días de deuda', 'Último pago']);
      this.pacientes().forEach((p) => filas.push([p.patient_name, p.national_id ?? '', p.phone ?? '', n(p.total_charged), n(p.total_paid), n(p.balance), p.status, p.open_charges, p.days_pending ?? '', p.last_payment_on ?? '']));
    } else if (this.vista() === 'cargos') {
      filas.push(['Fecha', 'Paciente', 'Concepto', 'Valor', 'Abonado', 'Pendiente', 'Estado', 'En crédito', 'Días']);
      this.cargos().forEach((c) => filas.push([c.issued_on, c.patient_name, c.description, n(c.amount), n(c.paid), n(c.pending), c.status, c.in_credit ? 'Sí' : 'No', c.days_open]));
    } else {
      filas.push(['Paciente', 'Tratamiento', 'Pieza', 'Plan', 'Profesional', 'Estado', 'Valor', 'Fecha estimada', 'Terminado']);
      this.tratamientos().forEach((t) => filas.push([t.patient_name, t.treatment, t.fdi_number ?? '', t.plan_title, t.professional_name ?? '', ESTADO_TRAT[t.status] ?? t.status, n(t.net_price), t.estimated_date ?? '', t.completed_date ?? '']));
    }
    const csv = 'sep=;\n' + filas.map((f) => f.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(';')).join('\n');
    const url = URL.createObjectURL(new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `cartera-${this.vista()}-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  iniciales(n: string): string {
    return n.split(' ').filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase();
  }
}
