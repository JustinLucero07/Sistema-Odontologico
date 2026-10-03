import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatMenuModule } from '@angular/material/menu';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import {
  CashSessionRow,
  Expense,
  FinanceSummary,
  PaymentRow,
  formatMoney,
} from '../../core/models/finance.models';
import { FinanceService } from '../../core/services/finance.service';
import { promptVoidReason } from '../../shared/confirm-dialog/prompt-dialog.component';
import { openExpenseDialog } from '../../shared/finance/expense-dialog.component';
import { SkeletonComponent } from '../../shared/skeleton/skeleton.component';

type View = 'resumen' | 'cobros' | 'egresos' | 'cajas';
type Preset = 'mes' | 'mes_anterior' | 'trimestre' | 'anio' | 'personalizado';

function iso(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

const MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

@Component({
  selector: 'app-finance-page',
  standalone: true,
  imports: [SkeletonComponent, 
    DatePipe,
    FormsModule,
    RouterLink,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatTooltipModule,
  ],
  templateUrl: './finance-page.component.html',
  styleUrl: './finance-page.component.scss',
})
export class FinancePageComponent implements OnInit {
  private readonly finance = inject(FinanceService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  readonly auth = inject(AuthService);

  readonly view = signal<View>('resumen');
  readonly preset = signal<Preset>('mes');
  readonly from = signal(iso(new Date(new Date().getFullYear(), new Date().getMonth(), 1)));
  readonly to = signal(iso(new Date()));

  readonly summary = signal<FinanceSummary | null>(null);
  readonly payments = signal<PaymentRow[]>([]);
  readonly expenses = signal<Expense[]>([]);
  readonly sessions = signal<CashSessionRow[]>([]);
  readonly loading = signal(true);

  readonly money = formatMoney;
  readonly canWrite = this.auth.hasPermission('payments:write');

  readonly presets: { code: Preset; label: string }[] = [
    { code: 'mes', label: 'Este mes' },
    { code: 'mes_anterior', label: 'Mes anterior' },
    { code: 'trimestre', label: 'Últimos 3 meses' },
    { code: 'anio', label: 'Este año' },
  ];

  readonly livePayments = computed(() => this.payments().filter((p) => !p.voided_at));
  readonly liveExpenses = computed(() => this.expenses().filter((e) => !e.voided_at));
  readonly paymentsTotal = computed(() => this.livePayments().reduce((s, p) => s + Number(p.amount), 0));
  readonly expensesTotal = computed(() => this.liveExpenses().reduce((s, e) => s + Number(e.amount), 0));

  /** Barras mensuales: ingresos y egresos lado a lado, sobre una escala común. */
  readonly chart = computed(() => {
    const months = this.summary()?.monthly ?? [];
    const max = Math.max(1, ...months.flatMap((m) => [Number(m.income), Number(m.expenses)]));
    return months.map((m) => {
      const [year, month] = m.month.split('-');
      return {
        label: `${MONTHS[Number(month) - 1]} ${year.slice(2)}`,
        income: Number(m.income),
        expenses: Number(m.expenses),
        net: Number(m.net),
        incomePct: (Number(m.income) / max) * 100,
        expensesPct: (Number(m.expenses) / max) * 100,
      };
    });
  });

  readonly maxMethod = computed(() => Math.max(1, ...(this.summary()?.income_by_method ?? []).map((b) => Number(b.total))));
  readonly maxCategory = computed(() =>
    Math.max(1, ...(this.summary()?.expenses_by_category ?? []).map((b) => Number(b.total))),
  );

  async ngOnInit(): Promise<void> {
    await this.reload();
  }

  setPreset(code: Preset): void {
    const now = new Date();
    const y = now.getFullYear();
    const m = now.getMonth();
    const ranges: Record<Exclude<Preset, 'personalizado'>, [Date, Date]> = {
      mes: [new Date(y, m, 1), now],
      mes_anterior: [new Date(y, m - 1, 1), new Date(y, m, 0)],
      trimestre: [new Date(y, m - 2, 1), now],
      anio: [new Date(y, 0, 1), now],
    };
    this.preset.set(code);
    if (code !== 'personalizado') {
      const [a, b] = ranges[code];
      this.from.set(iso(a));
      this.to.set(iso(b));
    }
    void this.reload();
  }

  setCustom(which: 'from' | 'to', value: string): void {
    if (!value) return;
    (which === 'from' ? this.from : this.to).set(value);
    this.preset.set('personalizado');
    void this.reload();
  }

  async reload(): Promise<void> {
    if (this.from() > this.to()) {
      this.snackBar.open('La fecha inicial es posterior a la final', 'Cerrar', { duration: 3000 });
      return;
    }
    this.loading.set(true);
    try {
      const [summary, payments, expenses, sessions] = await Promise.all([
        firstValueFrom(this.finance.getSummary(this.from(), this.to())),
        firstValueFrom(this.finance.listPayments(this.from(), this.to())),
        firstValueFrom(this.finance.listExpenses(this.from(), this.to())),
        firstValueFrom(this.finance.listCashSessions()),
      ]);
      this.summary.set(summary);
      this.payments.set(payments);
      this.expenses.set(expenses);
      this.sessions.set(sessions);
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.snackBar.open(typeof detail === 'string' ? detail : 'No se pudieron cargar las finanzas', 'Cerrar', {
        duration: 4000,
      });
    } finally {
      this.loading.set(false);
    }
  }

  async newExpense(): Promise<void> {
    const saved = await openExpenseDialog(this.dialog);
    if (saved) {
      this.snackBar.open('Egreso registrado', 'Cerrar', { duration: 3000 });
      await this.reload();
    }
  }

  async editExpense(expense: Expense): Promise<void> {
    const saved = await openExpenseDialog(this.dialog, expense);
    if (saved) await this.reload();
  }

  async voidExpense(expense: Expense): Promise<void> {
    const reason = await promptVoidReason(this.dialog, 'egreso');
    if (!reason) return;
    await firstValueFrom(this.finance.voidExpense(expense.id, reason));
    this.snackBar.open('Egreso anulado', 'Cerrar', { duration: 3000 });
    await this.reload();
  }

  async exportCsv(kind: 'payments' | 'expenses'): Promise<void> {
    const blob = await firstValueFrom(this.finance.downloadCsv(kind, this.from(), this.to()));
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${kind === 'payments' ? 'cobros' : 'egresos'}-${this.from()}-${this.to()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  diffClass(value: string | null): string {
    if (value === null) return '';
    const n = Number(value);
    return n === 0 ? 'ok' : n < 0 ? 'short' : 'over';
  }
}
