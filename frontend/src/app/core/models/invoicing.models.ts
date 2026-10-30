export type InvoiceStatus = 'pendiente' | 'recibida' | 'autorizada' | 'devuelta' | 'no_autorizada' | 'descartada';

export const INVOICE_STATUS_LABELS: Record<InvoiceStatus, string> = {
  pendiente: 'Pendiente de envío',
  recibida: 'En autorización',
  autorizada: 'Autorizada',
  devuelta: 'Devuelta por el SRI',
  no_autorizada: 'No autorizada',
  descartada: 'Descartada',
};

export interface SriMessage {
  identificador: string;
  mensaje: string;
  informacion: string;
  tipo: string;
}

export interface InvoiceLine {
  id: string;
  charge_id: string | null;
  code: string;
  description: string;
  quantity: string;
  unit_price: string;
  discount: string;
  subtotal: string;
  vat_code: string;
  vat_rate: string;
  vat: string;
}

export interface Invoice {
  id: string;
  doc_type: '01' | '04';
  number: string;
  patient_id: string | null;
  modified_invoice_id: string | null;
  reason: string | null;
  environment: '1' | '2';
  access_key: string;
  issue_date: string;
  buyer_id_type: string;
  buyer_id: string;
  buyer_name: string;
  buyer_email: string | null;
  buyer_address: string | null;
  buyer_phone: string | null;
  payment_method: string;
  subtotal: string;
  discount: string;
  vat: string;
  total: string;
  notes: string | null;
  status: InvoiceStatus;
  sri_messages: SriMessage[];
  authorized_at: string | null;
  attempts: number;
  next_attempt_at: string | null;
  last_error: string | null;
  emailed_at: string | null;
  discarded_at: string | null;
  discard_reason: string | null;
  created_at: string;
  lines: InvoiceLine[];
  credited: string;
}

export interface InvoicingSettings {
  environment: '1' | '2';
  send_email: boolean;
  retention_agent: string | null;
  has_certificate: boolean;
  certificate_subject: string | null;
  certificate_valid_until: string | null;
  certificate_expired: boolean;
  email_configured: boolean;
  next_invoice_number: number;
  establishment: string;
  emission_point: string;
  missing: string[];
}

export interface Option {
  code: string;
  label: string;
  rate?: string;
}

export interface InvoicingCatalogs {
  vat: Option[];
  id_types: Option[];
  payment_methods: Option[];
  statuses: Option[];
  environments: Option[];
}

export interface InvoiceableCharge {
  id: string;
  description: string;
  amount: string;
  issued_on: string;
}

export interface InvoiceItemIn {
  charge_id?: string | null;
  code?: string | null;
  description?: string | null;
  quantity?: string;
  unit_price?: string | null;
  price_includes_vat?: boolean;
  discount?: string;
  vat_code: string;
}

export interface InvoiceCreate {
  patient_id?: string | null;
  buyer?: {
    id_type: string;
    id_number: string;
    name: string;
    email?: string | null;
    address?: string | null;
    phone?: string | null;
  } | null;
  items: InvoiceItemIn[];
  payment_method: string;
  notes?: string | null;
}

/** De la caja al SRI: la forma de pago que corresponde a cada medio. */
export const SRI_PAYMENT_FROM_METHOD: Record<string, string> = {
  efectivo: '01',
  tarjeta_debito: '16',
  tarjeta_credito: '19',
  transferencia: '20',
  deposito: '20',
  cheque: '20',
  seguro: '20',
  otro: '01',
};
