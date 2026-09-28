import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  AccountStatement,
  CashSession,
  CashSessionRow,
  Charge,
  DailyCashReport,
  Expense,
  ExpenseCategory,
  ExpenseInput,
  FinanceSummary,
  Payment,
  PaymentMethodOption,
  PaymentRow,
} from '../models/finance.models';

export interface PaymentInput {
  amount: string;
  method: string;
  charge_id?: string | null;
  reference?: string | null;
  received_on?: string | null;
  notes?: string | null;
}

@Injectable({ providedIn: 'root' })
export class FinanceService {
  private readonly http = inject(HttpClient);

  getMethods(): Observable<PaymentMethodOption[]> {
    return this.http.get<PaymentMethodOption[]>(`${environment.apiUrl}/finance/payment-methods`);
  }

  getAccount(patientId: string): Observable<AccountStatement> {
    return this.http.get<AccountStatement>(`${environment.apiUrl}/patients/${patientId}/account`);
  }

  createCharge(
    patientId: string,
    body: { description: string; amount: string; issued_on?: string | null; notes?: string | null },
  ): Observable<Charge> {
    return this.http.post<Charge>(`${environment.apiUrl}/patients/${patientId}/charges`, body);
  }

  createPayment(patientId: string, body: PaymentInput): Observable<Payment> {
    return this.http.post<Payment>(`${environment.apiUrl}/patients/${patientId}/payments`, body);
  }

  /** There is no delete for money. A mistake is reversed in place, with a
   *  reason, so the day's till still reconciles against what happened. */
  voidPayment(paymentId: string, reason: string): Observable<Payment> {
    return this.http.post<Payment>(`${environment.apiUrl}/finance/payments/${paymentId}/void`, {
      reason,
    });
  }

  voidCharge(chargeId: string, reason: string): Observable<Charge> {
    return this.http.post<Charge>(`${environment.apiUrl}/finance/charges/${chargeId}/void`, {
      reason,
    });
  }

  setInstallments(
    chargeId: string,
    body: { count: number; first_due_on: string; every_days?: number },
  ): Observable<Charge> {
    return this.http.post<Charge>(
      `${environment.apiUrl}/finance/charges/${chargeId}/installments`,
      body,
    );
  }

  getOpenCashSession(): Observable<CashSession | null> {
    return this.http.get<CashSession | null>(`${environment.apiUrl}/finance/cash-session`);
  }

  openCashSession(openingFloat: string): Observable<CashSession> {
    return this.http.post<CashSession>(`${environment.apiUrl}/finance/cash-session/open`, {
      opening_float: openingFloat,
    });
  }

  closeCashSession(countedCash: string, notes?: string | null): Observable<CashSession> {
    return this.http.post<CashSession>(`${environment.apiUrl}/finance/cash-session/close`, {
      counted_cash: countedCash,
      notes: notes ?? null,
    });
  }

  getDailyReport(day?: string): Observable<DailyCashReport> {
    const query = day ? `?day=${day}` : '';
    return this.http.get<DailyCashReport>(`${environment.apiUrl}/finance/daily-report${query}`);
  }

  // ---- Egresos, resumen y listados -------------------------------------

  private range(from: string, to: string) {
    return { date_from: from, date_to: to };
  }

  getExpenseCategories(): Observable<ExpenseCategory[]> {
    return this.http.get<ExpenseCategory[]>(`${environment.apiUrl}/finance/expense-categories`);
  }

  listExpenses(from: string, to: string): Observable<Expense[]> {
    return this.http.get<Expense[]>(`${environment.apiUrl}/finance/expenses`, { params: this.range(from, to) });
  }

  createExpense(body: ExpenseInput): Observable<Expense> {
    return this.http.post<Expense>(`${environment.apiUrl}/finance/expenses`, body);
  }

  updateExpense(id: string, body: ExpenseInput): Observable<Expense> {
    return this.http.put<Expense>(`${environment.apiUrl}/finance/expenses/${id}`, body);
  }

  voidExpense(id: string, reason: string): Observable<Expense> {
    return this.http.post<Expense>(`${environment.apiUrl}/finance/expenses/${id}/void`, { reason });
  }

  getSummary(from: string, to: string): Observable<FinanceSummary> {
    return this.http.get<FinanceSummary>(`${environment.apiUrl}/finance/summary`, { params: this.range(from, to) });
  }

  listPayments(from: string, to: string): Observable<PaymentRow[]> {
    return this.http.get<PaymentRow[]>(`${environment.apiUrl}/finance/payments`, { params: this.range(from, to) });
  }

  listCashSessions(): Observable<CashSessionRow[]> {
    return this.http.get<CashSessionRow[]>(`${environment.apiUrl}/finance/cash-sessions`);
  }

  downloadCsv(kind: 'payments' | 'expenses', from: string, to: string): Observable<Blob> {
    return this.http.get(`${environment.apiUrl}/finance/${kind}.csv`, {
      params: this.range(from, to),
      responseType: 'blob',
    });
  }
}
