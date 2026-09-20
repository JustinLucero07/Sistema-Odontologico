import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { formatMoney } from '../../core/models/finance.models';
import {
  AppointmentReport,
  ClinicalReport,
  FinancialReport,
  PatientReport,
  REPORT_TABS,
  ReportKind,
  ReportSummary,
  formatRate,
} from '../../core/models/report.models';
import { ReportsService } from '../../core/services/reports.service';

/** Named ranges cover what a clinic actually asks for; the custom dates stay
 *  available for everything else. */
const PRESETS = [
  { key: 'month', label: 'Este mes' },
  { key: 'last_month', label: 'Mes pasado' },
  { key: 'quarter', label: 'Últimos 90 días' },
  { key: 'year', label: 'Este año' },
] as const;

type PresetKey = (typeof PRESETS)[number]['key'];

@Component({
  selector: 'app-reports-page',
  standalone: true,
  imports: [DatePipe, FormsModule, MatButtonModule, MatFormFieldModule, MatIconModule, MatInputModule],
  templateUrl: './reports-page.component.html',
  styleUrl: './reports-page.component.scss',
})
export class ReportsPageComponent implements OnInit {
  private readonly reports = inject(ReportsService);
  private readonly snackBar = inject(MatSnackBar);

  readonly tabs = REPORT_TABS;
  readonly presets = PRESETS;
  readonly money = formatMoney;
  readonly rate = formatRate;

  readonly active = signal<ReportKind>('financial');
  readonly loading = signal(true);
  readonly downloading = signal(false);

  readonly summary = signal<ReportSummary | null>(null);
  readonly financial = signal<FinancialReport | null>(null);
  readonly clinical = signal<ClinicalReport | null>(null);
  readonly appointments = signal<AppointmentReport | null>(null);
  readonly patients = signal<PatientReport | null>(null);

  dateFrom = '';
  dateTo = '';
  readonly activePreset = signal<PresetKey | null>('month');

  constructor() {
    this.applyPreset('month', false);
  }

  async ngOnInit(): Promise<void> {
    await this.reload();
  }

  private iso(d: Date): string {
    // Local date parts, not toISOString: that shifts to UTC and can move the
    // range a day for anyone west of Greenwich.
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }

  applyPreset(key: PresetKey, reload = true): void {
    const today = new Date();
    let from: Date;
    let to = today;

    switch (key) {
      case 'month':
        from = new Date(today.getFullYear(), today.getMonth(), 1);
        break;
      case 'last_month':
        from = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        to = new Date(today.getFullYear(), today.getMonth(), 0);
        break;
      case 'quarter':
        from = new Date(today);
        from.setDate(from.getDate() - 89);
        break;
      case 'year':
        from = new Date(today.getFullYear(), 0, 1);
        break;
    }

    this.dateFrom = this.iso(from);
    this.dateTo = this.iso(to);
    this.activePreset.set(key);
    if (reload) void this.reload();
  }

  onCustomRange(): void {
    this.activePreset.set(null);
    void this.reload();
  }

  async select(kind: ReportKind): Promise<void> {
    this.active.set(kind);
    await this.reload();
  }

  async reload(): Promise<void> {
    if (!this.dateFrom || !this.dateTo) return;
    this.loading.set(true);
    try {
      const [summary] = await Promise.all([
        firstValueFrom(this.reports.getSummary(this.dateFrom, this.dateTo)),
        this.loadActive(),
      ]);
      this.summary.set(summary);
    } catch (error) {
      const detail = (error as { error?: { detail?: unknown } })?.error?.detail;
      this.snackBar.open(
        typeof detail === 'string' ? detail : 'No se pudo cargar el reporte',
        'Cerrar',
        { duration: 7000 },
      );
    } finally {
      this.loading.set(false);
    }
  }

  /** Only the visible report is fetched; switching tabs fetches that one. */
  private async loadActive(): Promise<void> {
    const from = this.dateFrom;
    const to = this.dateTo;
    switch (this.active()) {
      case 'financial':
        this.financial.set(await firstValueFrom(this.reports.getFinancial(from, to)));
        break;
      case 'clinical':
        this.clinical.set(await firstValueFrom(this.reports.getClinical(from, to)));
        break;
      case 'appointments':
        this.appointments.set(await firstValueFrom(this.reports.getAppointments(from, to)));
        break;
      case 'patients':
        this.patients.set(await firstValueFrom(this.reports.getPatients(from, to)));
        break;
    }
  }

  async download(): Promise<void> {
    if (this.downloading()) return;
    this.downloading.set(true);
    try {
      const kind = this.active();
      const blob = await firstValueFrom(this.reports.downloadCsv(kind, this.dateFrom, this.dateTo));
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${kind}-${this.dateFrom}-${this.dateTo}.csv`;
      link.click();
      // Released immediately: the download has already been handed to the
      // browser, and a held blob URL keeps the whole file in memory.
      URL.revokeObjectURL(url);
    } catch {
      this.snackBar.open('No se pudo descargar el CSV', 'Cerrar', { duration: 5000 });
    } finally {
      this.downloading.set(false);
    }
  }

  // ---- Chart helpers ----------------------------------------------------

  /** Bars are scaled against the largest value present, so the shortest bar is
   *  still visible and the comparison is between the series' own members. */
  share(value: string | number, max: number): number {
    const n = typeof value === 'number' ? value : Number(value);
    return max > 0 ? (n / max) * 100 : 0;
  }

  maxAmount(rows: { amount: string }[]): number {
    return Math.max(...rows.map((r) => Number(r.amount)), 0);
  }

  maxCount(rows: { count: number }[]): number {
    return Math.max(...rows.map((r) => r.count), 0);
  }

  // ---- Daily income sparkline ------------------------------------------

  readonly dailyPath = computed(() => {
    const rows = this.financial()?.daily ?? [];
    if (rows.length < 2) return '';
    const values = rows.map((r) => Number(r.amount));
    const max = Math.max(...values, 1);
    const step = 100 / (rows.length - 1);
    return values
      .map((v, i) => `${i === 0 ? 'M' : 'L'} ${(i * step).toFixed(2)} ${(30 - (v / max) * 28).toFixed(2)}`)
      .join(' ');
  });

  readonly dailyPeak = computed(() => {
    const rows = this.financial()?.daily ?? [];
    if (rows.length === 0) return null;
    return rows.reduce((best, row) => (Number(row.amount) > Number(best.amount) ? row : best));
  });
}
