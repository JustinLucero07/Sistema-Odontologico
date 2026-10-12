import { DatePipe } from '@angular/common';
import { Component, OnInit, TemplateRef, ViewChild, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { confirmAction } from '../../shared/confirm-dialog/confirm-dialog.component';
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
  ExpenseCategory,
  FinanceSummary,
  PaymentMethodOption,
  Projection,
  RecurringExpense,
  PaymentRow,
  formatMoney,
} from '../../core/models/finance.models';
import { FinanceService } from '../../core/services/finance.service';
import { promptVoidReason } from '../../shared/confirm-dialog/prompt-dialog.component';
import { openExpenseDialog } from '../../shared/finance/expense-dialog.component';
import { SkeletonComponent } from '../../shared/skeleton/skeleton.component';

type View = 'resumen' | 'cobros' | 'egresos' | 'fijos' | 'proyeccion' | 'cajas';
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
    MatDialogModule,
    MatSelectModule,
    MatSlideToggleModule,
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
    void this.loadRecurring();
    void this.loadProjection();
  }

  // ---- Gastos fijos -----------------------------------------------------

  @ViewChild('recurringDialog') recurringDialog!: TemplateRef<unknown>;
  private recurringRef: MatDialogRef<unknown> | null = null;
  readonly recurring = signal<RecurringExpense[]>([]);
  readonly categories = signal<ExpenseCategory[]>([]);
  readonly methods = signal<PaymentMethodOption[]>([]);
  readonly editingRecurring = signal<RecurringExpense | null>(null);
  readonly recurringError = signal<string | null>(null);
  rec = { description: '', category: 'arriendo', amount: '', method: 'transferencia', day_of_month: 5, supplier_name: '', is_active: true };

  readonly recurringPending = computed(() => this.recurring().filter((r) => r.due_this_month));
  readonly recurringMonthly = computed(() =>
    this.recurring().filter((r) => r.is_active).reduce((s, r) => s + Number(r.amount), 0),
  );
  readonly recurringPendingTotal = computed(() => this.recurringPending().reduce((s, r) => s + Number(r.amount), 0));

  async loadRecurring(): Promise<void> {
    try {
      this.recurring.set(await firstValueFrom(this.finance.listRecurring()));
    } catch {
      this.recurring.set([]);
    }
  }

  async openRecurring(r: RecurringExpense | null): Promise<void> {
    if (!this.categories().length) {
      const [c, m] = await Promise.all([
        firstValueFrom(this.finance.getExpenseCategories()),
        firstValueFrom(this.finance.getMethods()),
      ]);
      this.categories.set(c);
      this.methods.set(m);
    }
    this.editingRecurring.set(r);
    this.recurringError.set(null);
    this.rec = r
      ? { description: r.description, category: r.category, amount: String(r.amount), method: r.method, day_of_month: r.day_of_month, supplier_name: r.supplier_name ?? '', is_active: r.is_active }
      : { description: '', category: 'arriendo', amount: '', method: 'transferencia', day_of_month: 5, supplier_name: '', is_active: true };
    this.recurringRef = this.dialog.open(this.recurringDialog, { width: '560px', maxWidth: '96vw', panelClass: 'app-dialog' });
  }

  async saveRecurring(): Promise<void> {
    try {
      await firstValueFrom(
        this.finance.saveRecurring(
          { ...this.rec, amount: String(this.rec.amount).replace(',', '.'), supplier_name: this.rec.supplier_name || null },
          this.editingRecurring()?.id,
        ),
      );
      this.recurringRef?.close();
      await this.loadRecurring();
      void this.loadProjection();
    } catch (e: unknown) {
      const d = (e as { error?: { detail?: unknown } })?.error?.detail;
      this.recurringError.set(typeof d === 'string' ? d : 'Revise los datos: descripción, monto y día (1 a 28).');
    }
  }

  async deleteRecurring(r: RecurringExpense): Promise<void> {
    const ok = await confirmAction(this.dialog, {
      title: `¿Eliminar «${r.description}»?`,
      message: 'Solo se quita la plantilla. Los egresos que ya registró con ella se conservan.',
      confirmLabel: 'Eliminar',
      danger: true,
    });
    if (!ok) return;
    await firstValueFrom(this.finance.deleteRecurring(r.id));
    await this.loadRecurring();
    void this.loadProjection();
  }

  async registerRecurring(r: RecurringExpense): Promise<void> {
    try {
      await firstValueFrom(this.finance.registerRecurring(r.id));
      this.snackBar.open(`«${r.description}» registrado como egreso de este mes`, 'Cerrar', { duration: 3500 });
      await Promise.all([this.loadRecurring(), this.reload()]);
      void this.loadProjection();
    } catch (e: unknown) {
      const d = (e as { error?: { detail?: unknown } })?.error?.detail;
      this.snackBar.open(typeof d === 'string' ? d : 'No se pudo registrar', 'Cerrar', { duration: 4000 });
    }
  }

  // ---- Proyección -------------------------------------------------------

  readonly projDays = signal(30);
  readonly projection = signal<Projection | null>(null);

  async loadProjection(days = this.projDays()): Promise<void> {
    this.projDays.set(days);
    try {
      this.projection.set(await firstValueFrom(this.finance.getProjection(days)));
    } catch {
      this.projection.set(null);
    }
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
