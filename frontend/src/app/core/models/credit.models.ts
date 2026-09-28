export type CreditStatus = 'al_dia' | 'vencido' | 'pagado' | 'anulado';
export type CreditFrequency = 'semanal' | 'quincenal' | 'mensual';

export const CREDIT_STATUS_LABELS: Record<CreditStatus, string> = {
  al_dia: 'Al día',
  vencido: 'Con atraso',
  pagado: 'Pagado',
  anulado: 'Anulado',
};

export const INSTALLMENT_STATUS_LABELS: Record<string, string> = {
  pagada: 'Pagada',
  parcial: 'Parcial',
  pendiente: 'Pendiente',
  vencida: 'Vencida',
};

export interface CreditOptions {
  frequencies: { code: CreditFrequency; label: string; days: number }[];
  max_installments: number;
  max_monthly_rate: number;
}

export interface CreditPreview {
  rows: { number: number; due_on: string; principal: string; interest: string; amount: string }[];
  total: string;
  total_interest: string;
  installment_amount: string;
  annual_rate: string;
}

export interface CreditInstallmentRow {
  number: number;
  due_on: string;
  principal: string;
  interest: string;
  amount: string;
  paid: string;
  pending: string;
  status: 'pagada' | 'parcial' | 'pendiente' | 'vencida';
  days_late: number;
}

export interface CreditPaymentRow {
  group_id: string;
  received_on: string;
  amount: string;
  method: string;
  method_label: string;
  reference: string | null;
  voided_at: string | null;
  void_reason: string | null;
  payment_ids: string[];
}

export interface Credit {
  id: string;
  patient_id: string;
  patient_name: string;
  patient_phone: string | null;
  charge_id: string;
  charge_description: string;
  interest_charge_id: string | null;
  down_payment: string;
  principal: string;
  monthly_rate: string;
  frequency: CreditFrequency;
  frequency_label: string;
  installment_count: number;
  first_due_on: string;
  total: string;
  total_interest: string;
  paid: string;
  pending: string;
  overdue: string;
  days_late: number;
  next_due_on: string | null;
  next_amount: string | null;
  status: CreditStatus;
  guarantor_name: string | null;
  guarantor_id_number: string | null;
  guarantor_phone: string | null;
  notes: string | null;
  created_at: string;
  voided_at: string | null;
  void_reason: string | null;
  /** false si el paciente retiró su autorización de mensajes. */
  communications_allowed: boolean;
}

export interface CreditDetail extends Credit {
  installments: CreditInstallmentRow[];
  payments: CreditPaymentRow[];
}

export interface CreditSummary {
  active_count: number;
  overdue_count: number;
  outstanding: string;
  overdue_amount: string;
  collected_this_month: string;
}

export interface CreditCreate {
  charge_id: string;
  installment_count: number;
  frequency: CreditFrequency;
  first_due_on: string;
  monthly_rate: string;
  down_payment: string;
  down_payment_method: string;
  down_payment_reference?: string | null;
  guarantor_name?: string | null;
  guarantor_id_number?: string | null;
  guarantor_phone?: string | null;
  notes?: string | null;
}
