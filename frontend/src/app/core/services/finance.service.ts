import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  AccountStatement,
  CashSession,
  Charge,
  DailyCashReport,
  Payment,
  PaymentMethodOption,
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
}
