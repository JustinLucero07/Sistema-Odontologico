import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import {
  APPOINTMENT_STATUS_COLORS,
  APPOINTMENT_STATUS_LABELS,
  AppointmentStatus,
} from '../../core/models/appointment.models';
import { AgendaEntry, DashboardService, DashboardSummary } from '../../core/services/dashboard.service';
import { ToothMarkComponent } from '../../shared/brand/tooth-mark.component';
import { openPatientCreateDialog } from '../../shared/patient-dialog/patient-create-dialog.component';

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

/** "1 cita" / "3 citas": los "(s)" se leen como un formulario, no como una frase. */
function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
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
  imports: [MatButtonModule, MatIconModule, MatTooltipModule, RouterLink, ToothMarkComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit, OnDestroy {
  readonly auth = inject(AuthService);
  private readonly dashboardService = inject(DashboardService);
  private readonly router = inject(Router);
  private readonly dialog = inject(MatDialog);

  readonly summary = signal<DashboardSummary | null>(null);
  readonly loading = signal(true);

  readonly chart = CHART;
  readonly donutRadius = DONUT_RADIUS;

  /** Index of the day the pointer is nearest, or null when it has left. */
  readonly hoverDay = signal<number | null>(null);
  /** Status hovered in the donut or its legend — drives the centre readout. */
  readonly hoverStatus = signal<AppointmentStatus | null>(null);

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

  /** Reloj del panel: avanza cada minuto para que "ahora" y "la próxima cita"
   *  sigan siendo ciertos si la pantalla se queda abierta toda la mañana. */
  readonly now = signal(Date.now());
  private clock: ReturnType<typeof setInterval> | null = null;

  readonly statusLabels = APPOINTMENT_STATUS_LABELS;
  readonly statusColors = APPOINTMENT_STATUS_COLORS;

  // ---- Agenda de hoy -----------------------------------------------------

  readonly agenda = computed<AgendaEntry[]>(() => this.summary()?.today_agenda ?? []);

  /** La siguiente cita que todavía no empezó (o está en curso) y no se cerró. */
  readonly nextAppointment = computed<AgendaEntry | null>(() => {
    const now = this.now();
    return (
      this.agenda().find(
        (a) => new Date(a.ends_at).getTime() > now && !['atendida', 'no_asistio'].includes(a.status),
      ) ?? null
    );
  });

  readonly doneCount = computed(() => this.agenda().filter((a) => a.status === 'atendida').length);

  /** Anillo del día: la parte de la agenda ya atendida. */
  readonly dayProgress = computed(() => {
    const total = this.agenda().length;
    const done = this.doneCount();
    const circumference = 2 * Math.PI * 34;
    const fraction = total ? done / total : 0;
    return { total, done, dash: `${fraction * circumference} ${circumference}` };
  });

  /** Una frase que resume el día, en vez de obligar a leer los números. */
  readonly narrative = computed(() => {
    const data = this.summary();
    if (!data) return '';
    const count = data.appointments_today;
    const next = this.nextAppointment();
    if (count === 0) return 'No hay citas para hoy. Buen momento para confirmar las de mañana.';
    const head = count === 1 ? 'Hoy hay 1 cita' : `Hoy hay ${count} citas`;
    if (!next) return `${head} y ya se atendieron todas.`;
    return `${head}. La próxima es ${next.patient_name} a las ${this.time(next.starts_at)}.`;
  });

  isPast(entry: AgendaEntry): boolean {
    return new Date(entry.ends_at).getTime() <= this.now();
  }

  isNow(entry: AgendaEntry): boolean {
    const now = this.now();
    return new Date(entry.starts_at).getTime() <= now && new Date(entry.ends_at).getTime() > now;
  }

  time(iso: string): string {
    return new Date(iso).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' });
  }

  minutesUntil(entry: AgendaEntry): string {
    const minutes = Math.round((new Date(entry.starts_at).getTime() - this.now()) / 60000);
    if (minutes <= 0) return 'en curso';
    if (minutes < 60) return `en ${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const rest = minutes % 60;
    return rest ? `en ${hours} h ${rest} min` : `en ${hours} h`;
  }

  initials(name: string): string {
    const parts = name.split(' ').filter(Boolean);
    return `${parts[0]?.charAt(0) ?? ''}${parts[1]?.charAt(0) ?? ''}`.toUpperCase();
  }

  // ---- Dinero ------------------------------------------------------------

  readonly canSeeMoney = computed(() => this.summary()?.income_month != null);

  /** Mes en curso frente al mismo tramo del mes pasado. */
  readonly incomeTrend = computed<{ percent: number; up: boolean } | null>(() => {
    const data = this.summary();
    const current = Number(data?.income_month ?? 0);
    const previous = Number(data?.income_previous_month_same_period ?? 0);
    if (!data?.income_month || previous === 0) return null;
    const change = ((current - previous) / previous) * 100;
    return { percent: Math.abs(Math.round(change)), up: change >= 0 };
  });

  // ---- Requiere atención -------------------------------------------------

  readonly attention = computed(() => {
    const a = this.summary()?.attention;
    if (!a) return [];
    const items: { icon: string; tone: string; title: string; detail: string; route: string }[] = [];
    if (a.lab_overdue) {
      items.push({
        icon: 'precision_manufacturing',
        tone: 'danger',
        title: plural(a.lab_overdue, 'trabajo de laboratorio atrasado', 'trabajos de laboratorio atrasados'),
        detail: 'Ya pasó su fecha de entrega',
        route: '/laboratory',
      });
    }
    if (a.stock_alerts) {
      items.push({
        icon: 'inventory_2',
        tone: 'warning',
        title: plural(a.stock_alerts, 'artículo con alerta de stock', 'artículos con alerta de stock'),
        detail: 'Bajo el mínimo o por vencer',
        route: '/inventory',
      });
    }
    if (a.budgets_awaiting) {
      items.push({
        icon: 'request_quote',
        tone: 'accent',
        title: plural(a.budgets_awaiting, 'presupuesto sin respuesta', 'presupuestos sin respuesta'),
        detail: 'Un buen día para llamar al paciente',
        route: '/reports',
      });
    }
    return items;
  });

  readonly birthdays = computed(() => this.summary()?.attention.birthdays ?? []);

  whatsappLink(number: string, name: string): string {
    const text = encodeURIComponent(`¡Feliz cumpleaños, ${name.split(' ')[0]}! Le desea todo el equipo de la clínica.`);
    return `https://wa.me/${number.replace(/[^\d]/g, '')}?text=${text}`;
  }

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
    if (!data || data.budget_accepted_total === null || data.budget_awaiting_total === null) return null;
    const accepted = data.budget_accepted_total;
    const awaiting = data.budget_awaiting_total;
    const total = accepted + awaiting;
    if (total === 0) return null;
    return {
      acceptedPercent: (accepted / total) * 100,
      awaitingPercent: (awaiting / total) * 100,
      accepted,
      awaiting,
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
    this.clock = setInterval(() => this.now.set(Date.now()), 60_000);
    try {
      this.summary.set(await firstValueFrom(this.dashboardService.getSummary()));
    } finally {
      this.loading.set(false);
    }
  }

  ngOnDestroy(): void {
    if (this.clock) clearInterval(this.clock);
  }

  async newPatient(): Promise<void> {
    await this.goTo('#nuevo-paciente');
  }

  newAppointment(): void {
    this.router.navigate(['/agenda'], { queryParams: { nueva: 1 } });
  }

  async goTo(route: string): Promise<void> {
    if (route === '#nuevo-paciente') {
      const created = await openPatientCreateDialog(this.dialog);
      if (created) this.router.navigate(['/patients', created.id]);
      return;
    }
    this.router.navigate([route]);
  }
}
