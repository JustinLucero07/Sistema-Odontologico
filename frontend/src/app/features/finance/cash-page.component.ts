import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { CashSession, DailyCashReport, formatMoney } from '../../core/models/finance.models';
import { FinanceService } from '../../core/services/finance.service';

@Component({
  selector: 'app-cash-page',
  standalone: true,
  imports: [
    DatePipe,
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
  ],
  templateUrl: './cash-page.component.html',
  styleUrl: './cash-page.component.scss',
})
export class CashPageComponent implements OnInit {
  private readonly finance = inject(FinanceService);
  private readonly snackBar = inject(MatSnackBar);
  readonly auth = inject(AuthService);

  readonly session = signal<CashSession | null>(null);
  readonly report = signal<DailyCashReport | null>(null);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly closing = signal(false);

  readonly money = formatMoney;
  openingFloat = '0.00';
  countedCash = '';
  closeNotes = '';
  day = new Date().toISOString().slice(0, 10);

  get canWrite(): boolean {
    return this.auth.hasPermission('payments:write');
  }

  /** The largest method total sets the bar scale, so the bars compare against
   *  each other rather than against an arbitrary maximum. */
  readonly maxMethodTotal = computed(() =>
    Math.max(...(this.report()?.by_method.map((m) => Number(m.total)) ?? [0]), 1),
  );

  async ngOnInit(): Promise<void> {
    await this.reload();
  }

  private async reload(): Promise<void> {
    this.loading.set(true);
    try {
      const [session, report] = await Promise.all([
        firstValueFrom(this.finance.getOpenCashSession()),
        firstValueFrom(this.finance.getDailyReport(this.day)),
      ]);
      this.session.set(session);
      this.report.set(report);
    } finally {
      this.loading.set(false);
    }
  }

  async changeDay(value: string): Promise<void> {
    this.day = value;
    await this.reload();
  }

  async open(): Promise<void> {
    if (this.saving()) return;
    this.saving.set(true);
    try {
      await firstValueFrom(this.finance.openCashSession(this.openingFloat.replace(',', '.')));
      await this.reload();
      this.snackBar.open('Caja abierta', 'Cerrar', { duration: 3000 });
    } catch (error) {
      this.report_(error, 'No se pudo abrir la caja');
    } finally {
      this.saving.set(false);
    }
  }

  async close(): Promise<void> {
    if (this.saving() || !this.countedCash) return;
    this.saving.set(true);
    try {
      const closed = await firstValueFrom(
        this.finance.closeCashSession(this.countedCash.replace(',', '.'), this.closeNotes || null),
      );
      this.closing.set(false);
      this.countedCash = '';
      this.closeNotes = '';
      await this.reload();
      const difference = Number(closed.difference ?? 0);
      this.snackBar.open(
        difference === 0
          ? 'Caja cerrada y cuadrada'
          : `Caja cerrada con una diferencia de $ ${formatMoney(difference)}`,
        'Cerrar',
        { duration: 6000 },
      );
    } catch (error) {
      this.report_(error, 'No se pudo cerrar la caja');
    } finally {
      this.saving.set(false);
    }
  }

  private report_(error: unknown, fallback: string): void {
    const detail = (error as { error?: { detail?: unknown } })?.error?.detail;
    this.snackBar.open(typeof detail === 'string' ? detail : fallback, 'Cerrar', {
      duration: 7000,
    });
  }
}
