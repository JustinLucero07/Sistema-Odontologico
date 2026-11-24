import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';

export type AccountType = 'ahorros' | 'corriente' | 'otra';

export interface PaymentAccount {
  id: string;
  label: string;
  qr_data: string | null;
  holder_name: string | null;
  holder_id: string | null;
  account_type: AccountType | null;
  account_number: string | null;
  email: string | null;
  note: string | null;
  sort_order: number;
  is_active: boolean;
}

export type PaymentAccountFields = Partial<Omit<PaymentAccount, 'id' | 'sort_order'>>;

export const ACCOUNT_TYPE_LABEL: Record<AccountType, string> = {
  ahorros: 'Cuenta de ahorros',
  corriente: 'Cuenta corriente',
  otra: 'Otra',
};

export function accountText(a: PaymentAccount): string {
  return [
    `*${a.label}*`,
    a.account_type && a.account_number ? `${ACCOUNT_TYPE_LABEL[a.account_type]} N.º ${a.account_number}` : a.account_number ? `Cuenta N.º ${a.account_number}` : null,
    a.holder_name ? `Titular: ${a.holder_name}` : null,
    a.holder_id ? `C.I./RUC: ${a.holder_id}` : null,
    a.email ? `Correo: ${a.email}` : null,
    a.note,
  ]
    .filter(Boolean)
    .join('\n');
}

@Injectable({ providedIn: 'root' })
export class PaymentAccountsService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/payment-accounts`;

  list(all = false): Observable<PaymentAccount[]> {
    return this.http.get<PaymentAccount[]>(this.base, { params: all ? { all: 'true' } : {} });
  }

  create(body: PaymentAccountFields): Observable<PaymentAccount> {
    return this.http.post<PaymentAccount>(this.base, body);
  }

  update(id: string, body: PaymentAccountFields): Observable<PaymentAccount> {
    return this.http.put<PaymentAccount>(`${this.base}/${id}`, body);
  }

  remove(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }

  reorder(ids: string[]): Observable<PaymentAccount[]> {
    return this.http.post<PaymentAccount[]>(`${this.base}/reorder`, { ids });
  }
}
