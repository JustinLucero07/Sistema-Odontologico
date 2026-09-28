export type PaymentMethodCode =
  | 'efectivo'
  | 'tarjeta_debito'
  | 'tarjeta_credito'
  | 'transferencia'
  | 'deposito'
  | 'cheque'
  | 'seguro'
  | 'otro';

export interface PaymentMethodOption {
  code: PaymentMethodCode;
  label: string;
  /** Card and transfer need the number that matches the bank statement. */
  requires_reference: boolean;
}

export type ChargeStatus = 'pendiente' | 'parcial' | 'pagada' | 'anulada';
export type InstallmentState = 'pagada' | 'parcial' | 'pendiente' | 'vencida';

export interface InstallmentStatus {
  number: number;
  due_on: string;
  amount: string;
  paid: string;
  pending: string;
  status: InstallmentState;
}

export interface Charge {
  id: string;
  patient_id: string;
  budget_id: string | null;
  description: string;
  amount: string;
  issued_on: string;
  created_at: string;
  notes: string | null;
  voided_at: string | null;
  void_reason: string | null;
  paid: string;
  pending: string;
  status: ChargeStatus;
  installments: InstallmentStatus[];
}

export interface Payment {
  id: string;
  patient_id: string;
  charge_id: string | null;
  cash_session_id: string | null;
  amount: string;
  method: PaymentMethodCode;
  reference: string | null;
  received_on: string;
  received_by_id: string | null;
  created_at: string;
  notes: string | null;
  voided_at: string | null;
  void_reason: string | null;
}

export interface AccountStatement {
  patient_id: string;
  total_charged: string;
  total_paid: string;
  balance: string;
  /** Money received that no charge claims yet. */
  unallocated: string;
  overdue_amount: string;
  charges: Charge[];
  payments: Payment[];
}

export interface CashSession {
  id: string;
  opened_at: string;
  opened_by_id: string | null;
  opening_float: string;
  closed_at: string | null;
  closed_by_id: string | null;
  counted_cash: string | null;
  expected_cash: string | null;
  difference: string | null;
  notes: string | null;
  is_open: boolean;
  /** Solo en la caja abierta: efectivo que entró, que salió y lo que debería haber. */
  cash_in?: string | null;
  cash_out?: string | null;
  expected_now?: string | null;
}

export interface MethodBreakdown {
  method: PaymentMethodCode;
  label: string;
  total: string;
  count: number;
}

export interface DailyCashReport {
  day: string;
  total: string;
  payment_count: number;
  by_method: MethodBreakdown[];
  voided_total: string;
  voided_count: number;
  expenses_total: string;
  expenses_count: number;
  cash_expenses: string;
}

export interface ExpenseCategory {
  code: string;
  label: string;
}

export interface Expense {
  id: string;
  spent_on: string;
  category: string;
  category_label: string;
  description: string;
  amount: string;
  method: PaymentMethodCode;
  method_label: string;
  supplier_id: string | null;
  supplier_name: string | null;
  receipt_number: string | null;
  cash_session_id: string | null;
  notes: string | null;
  created_by_name: string | null;
  created_at: string;
  voided_at: string | null;
  void_reason: string | null;
}

export interface ExpenseInput {
  spent_on: string;
  category: string;
  description: string;
  supplier_id?: string | null;
  supplier_name?: string | null;
  receipt_number?: string | null;
  notes?: string | null;
  /** Solo al crear: el importe y el medio no se editan después. */
  amount?: string;
  method?: PaymentMethodCode;
}

export interface Breakdown {
  code: string;
  label: string;
  total: string;
  count: number;
}

export interface FinanceSummary {
  date_from: string;
  date_to: string;
  sales: string;
  income: string;
  expenses: string;
  net: string;
  receivables: string;
  income_by_method: Breakdown[];
  expenses_by_category: Breakdown[];
  monthly: { month: string; income: string; expenses: string; net: string }[];
}

export interface PaymentRow {
  id: string;
  received_on: string;
  patient_id: string;
  patient_name: string;
  concept: string | null;
  amount: string;
  method: PaymentMethodCode;
  method_label: string;
  reference: string | null;
  received_by_name: string | null;
  voided_at: string | null;
  void_reason: string | null;
}

export interface CashSessionRow {
  id: string;
  opened_at: string;
  closed_at: string | null;
  opened_by_name: string | null;
  closed_by_name: string | null;
  opening_float: string;
  cash_in: string;
  cash_out: string;
  expected_cash: string;
  counted_cash: string | null;
  difference: string | null;
  notes: string | null;
}

/** Amounts cross the wire as strings so no cent is lost to a JSON float on the
 *  way in. They are parsed only at the moment of display. */
export function formatMoney(value: string | number): string {
  const amount = typeof value === 'number' ? value : Number(value);
  return new Intl.NumberFormat('es', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

export const CHARGE_STATUS_LABELS: Record<ChargeStatus, string> = {
  pendiente: 'Pendiente',
  parcial: 'Pago parcial',
  pagada: 'Pagada',
  anulada: 'Anulada',
};

export const INSTALLMENT_LABELS: Record<InstallmentState, string> = {
  pagada: 'Pagada',
  parcial: 'Parcial',
  pendiente: 'Pendiente',
  vencida: 'Vencida',
};
