import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import {
  APPOINTMENT_STATUS_COLORS,
  APPOINTMENT_STATUS_LABELS,
  AppointmentStatus,
} from '../../core/models/appointment.models';
import { DashboardService, DashboardSummary } from '../../core/services/dashboard.service';

interface QuickLink {
  label: string;
  description: string;
  icon: string;
  route: string;
  permission: string;
}

interface DonutSegment {
  status: AppointmentStatus;
  label: string;
  count: number;
  percent: number;
  color: string;
  /** Pre-computed stroke-dasharray/offset so the SVG stays declarative. */
  dash: string;
  offset: number;
}

interface AreaPoint {
  x: number;
  y: number;
  count: number;
  day: string;
  weekday: string;
  isToday: boolean;
}

const DONUT_RADIUS = 62;
const DONUT_CIRCUMFERENCE = 2 * Math.PI * DONUT_RADIUS;

// Chart geometry lives in one place so the path, the grid and the hover layer
// can never drift apart.
const CHART = { w: 620, h: 210, left: 34, right: 14, top: 16, bottom: 30 };
const PLOT_W = CHART.w - CHART.left - CHART.right;
const PLOT_H = CHART.h - CHART.top - CHART.bottom;

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [MatIconModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
  readonly auth = inject(AuthService);
  private readonly dashboardService = inject(DashboardService);
  private readonly router = inject(Router);

  readonly summary = signal<DashboardSummary | null>(null);
  readonly loading = signal(true);

  readonly chart = CHART;
  readonly donutRadius = DONUT_RADIUS;

  /** Index of the day the pointer is nearest, or null when it has left. */
  readonly hoverDay = signal<number | null>(null);
  /** Status hovered in the donut or its legend — drives the centre readout. */
  readonly hoverStatus = signal<AppointmentStatus | null>(null);

  readonly quickLinks: QuickLink[] = [
    {
      label: 'Agenda',
      description: 'Citas del día y la semana',
      icon: 'event',
      route: '/agenda',
      permission: 'appointments:read',
    },
    {
      label: 'Pacientes',
      description: 'Buscar y registrar',
      icon: 'groups',
      route: '/patients',
      permission: 'patients:read',
    },
    {
      label: 'Odontograma',
      description: 'Abrir la boca de un paciente',
      icon: 'dentistry',
      route: '/odontogram',
      permission: 'odontogram:read',
    },
    {
      label: 'Presupuestos',
      description: 'Seguimiento y aceptación',
      icon: 'request_quote',
      route: '/budgets',
      permission: 'budgets:read',
    },
    {
      label: 'Tratamientos',
      description: 'Planes en curso',
      icon: 'assignment',
      route: '/treatment-plans',
      permission: 'treatment_plans:read',
    },
    {
      label: 'Reportes',
      description: 'Auditoría y actividad',
      icon: 'insights',
      route: '/audit',
      permission: 'audit:read',
    },
  ];

  get visibleQuickLinks(): QuickLink[] {
    return this.quickLinks.filter((link) => this.auth.hasPermission(link.permission));
  }

  /** "Buenos días" etc. — a greeting that is wrong at 3am reads as careless. */
  readonly greeting = computed(() => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Buenos días';
    if (hour < 19) return 'Buenas tardes';
    return 'Buenas noches';
  });

  readonly today = computed(() =>
    new Date().toLocaleDateString('es', { weekday: 'long', day: 'numeric', month: 'long' }),
  );

  // ---- Donut -------------------------------------------------------------

  readonly donutTotal = computed(() =>
    (this.summary()?.appointments_by_status ?? []).reduce((sum, d) => sum + d.count, 0),
  );

  readonly donut = computed<DonutSegment[]>(() => {
    const data = this.summary()?.appointments_by_status ?? [];
    const total = this.donutTotal();
    if (total === 0) return [];

    let consumed = 0;
    return data.map((entry) => {
      const fraction = entry.count / total;
      // 2px of surface between segments, as separation rather than a border.
      const length = Math.max(fraction * DONUT_CIRCUMFERENCE - 2, 1);
      const segment: DonutSegment = {
        status: entry.status,
        label: APPOINTMENT_STATUS_LABELS[entry.status],
        count: entry.count,
        percent: Math.round(fraction * 100),
        color: APPOINTMENT_STATUS_COLORS[entry.status],
        dash: `${length} ${DONUT_CIRCUMFERENCE - length}`,
        offset: -consumed,
      };
      consumed += fraction * DONUT_CIRCUMFERENCE;
      return segment;
    });
  });

  /** What the ring's centre reads: the hovered slice, else the whole total. */
  readonly donutFocus = computed(() => {
    const status = this.hoverStatus();
    const found = status ? this.donut().find((s) => s.status === status) : undefined;
    return found
      ? { value: String(found.count), caption: found.label, color: found.color }
      : { value: String(this.donutTotal()), caption: 'citas en 7 días', color: '' };
  });

  // ---- Area chart --------------------------------------------------------

  readonly areaMax = computed(() => {
    const data = this.summary()?.appointments_per_day ?? [];
    // Round the ceiling up so gridlines land on whole appointments, never 3.5.
    return Math.max(...data.map((d) => d.count), 1);
  });

  readonly points = computed<AreaPoint[]>(() => {
    const data = this.summary()?.appointments_per_day ?? [];
    if (data.length === 0) return [];
    const max = this.areaMax();
    const today = new Date().toISOString().slice(0, 10);
    const step = data.length > 1 ? PLOT_W / (data.length - 1) : 0;

    return data.map((entry, i) => {
      const date = new Date(`${entry.date}T00:00:00`);
      return {
        x: CHART.left + i * step,
        y: CHART.top + (1 - entry.count / max) * PLOT_H,
        count: entry.count,
        day: String(date.getDate()),
        weekday: date.toLocaleDateString('es', { weekday: 'short' }).replace('.', ''),
        isToday: entry.date === today,
      };
    });
  });

  /** Catmull-Rom converted to cubic béziers, with control points clamped to
   *  the plot so a spike can never bow the curve below zero appointments. */
  readonly linePath = computed(() => {
    const pts = this.points();
    if (pts.length < 2) return '';
    const bottom = CHART.top + PLOT_H;
    const clamp = (v: number) => Math.min(Math.max(v, CHART.top), bottom);

    let d = `M ${pts[0].x} ${pts[0].y}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[i - 1] ?? pts[i];
      const p1 = pts[i];
      const p2 = pts[i + 1];
      const p3 = pts[i + 2] ?? p2;
      const c1x = p1.x + (p2.x - p0.x) / 6;
      const c1y = clamp(p1.y + (p2.y - p0.y) / 6);
      const c2x = p2.x - (p3.x - p1.x) / 6;
      const c2y = clamp(p2.y - (p3.y - p1.y) / 6);
      d += ` C ${c1x} ${c1y}, ${c2x} ${c2y}, ${p2.x} ${p2.y}`;
    }
    return d;
  });

  readonly areaPath = computed(() => {
    const pts = this.points();
    const line = this.linePath();
    if (!line) return '';
    const bottom = CHART.top + PLOT_H;
    return `${line} L ${pts[pts.length - 1].x} ${bottom} L ${pts[0].x} ${bottom} Z`;
  });

  /** Four gridlines with their value labels, derived from the same scale. */
  readonly gridLines = computed(() => {
    const max = this.areaMax();
    const steps = Math.min(max, 4);
    return Array.from({ length: steps + 1 }, (_, i) => {
      const value = Math.round((max / steps) * i);
      return { value, y: CHART.top + (1 - value / max) * PLOT_H };
    });
  });

  readonly hoveredPoint = computed<AreaPoint | null>(() => {
    const i = this.hoverDay();
    return i === null ? null : (this.points()[i] ?? null);
  });

  trackPointer(event: PointerEvent): void {
    const svg = event.currentTarget as SVGSVGElement;
    const rect = svg.getBoundingClientRect();
    if (rect.width === 0) return;
    // Map the pointer back into viewBox units, then snap to the nearest day.
    const x = ((event.clientX - rect.left) / rect.width) * CHART.w;
    const pts = this.points();
    if (pts.length === 0) return;

    let nearest = 0;
    let best = Infinity;
    pts.forEach((p, i) => {
      const distance = Math.abs(p.x - x);
      if (distance < best) {
        best = distance;
        nearest = i;
      }
    });
    this.hoverDay.set(nearest);
  }

  /** Percentage across the plot, so the HTML tooltip can ride the SVG. */
  tooltipLeft(point: AreaPoint): number {
    return (point.x / CHART.w) * 100;
  }

  // ---- Stats -------------------------------------------------------------

  /** Week-over-week change in appointments — null when there is no previous
   * week to compare against, so the card shows nothing rather than a fake 0%. */
  readonly weeklyTrend = computed<{ percent: number; up: boolean } | null>(() => {
    const data = this.summary();
    if (!data || data.appointments_previous_week === 0) return null;
    const change =
      ((data.appointments_this_week - data.appointments_previous_week) /
        data.appointments_previous_week) *
      100;
    return { percent: Math.abs(Math.round(change)), up: change >= 0 };
  });

  /** Accepted vs awaiting, as a share of the two together — the split is the
   *  story, and the absolute amounts are printed beside it. */
  readonly budgetSplit = computed(() => {
    const data = this.summary();
    if (!data) return null;
    const total = data.budget_accepted_total + data.budget_awaiting_total;
    if (total === 0) return null;
    return {
      acceptedPercent: (data.budget_accepted_total / total) * 100,
      awaitingPercent: (data.budget_awaiting_total / total) * 100,
      accepted: data.budget_accepted_total,
      awaiting: data.budget_awaiting_total,
    };
  });

  money(value: number): string {
    const compact = value >= 10000;
    return new Intl.NumberFormat('es', {
      minimumFractionDigits: compact ? 0 : 2,
      maximumFractionDigits: compact ? 0 : 2,
    }).format(value);
  }

  async ngOnInit(): Promise<void> {
    try {
      this.summary.set(await firstValueFrom(this.dashboardService.getSummary()));
    } finally {
      this.loading.set(false);
    }
  }

  goTo(route: string): void {
    this.router.navigate([route]);
  }
}
