export type MessageChannel = 'whatsapp' | 'sms' | 'email';

export type MessageStatus = 'pendiente' | 'enviado' | 'fallido' | 'simulado' | 'cancelado';

export interface MessageTemplate {
  id: string;
  code: string;
  name: string;
  channel: MessageChannel;
  body: string;
  is_active: boolean;
}

export interface OutboundMessage {
  id: string;
  patient_id: string | null;
  appointment_id: string | null;
  channel: MessageChannel;
  to_address: string;
  body: string;
  status: MessageStatus;
  provider: string | null;
  provider_message_id: string | null;
  error: string | null;
  created_at: string;
  sent_at: string | null;
}

export interface ProviderStatus {
  provider: string;
  is_live: boolean;
  message: string;
}

export interface DispatchResult {
  due: number;
  sent: number;
  simulated: number;
  failed: number;
  skipped: number;
}

export const MESSAGE_STATUS_LABELS: Record<MessageStatus, string> = {
  pendiente: 'Pendiente',
  enviado: 'Enviado',
  fallido: 'Falló',
  simulado: 'Simulado',
  cancelado: 'Cancelado',
};

export type SuggestionStatus = 'borrador' | 'aceptado' | 'descartado';

export interface AiStatus {
  provider: string;
  is_available: boolean;
  model: string | null;
  message: string;
}

export interface AiSuggestion {
  id: string;
  patient_id: string;
  kind: string;
  request: string | null;
  context_used: string;
  output: string;
  model: string | null;
  provider: string | null;
  status: SuggestionStatus;
  created_by_id: string | null;
  created_at: string;
  accepted_by_id: string | null;
  decided_at: string | null;
  discard_reason: string | null;
}

export const SUGGESTION_STATUS_LABELS: Record<SuggestionStatus, string> = {
  borrador: 'Borrador',
  aceptado: 'Aceptado',
  descartado: 'Descartado',
};

export interface PortalLink {
  id: string;
  patient_id: string;
  expires_at: string;
  created_at: string;
  last_used_at: string | null;
  use_count: number;
  revoked_at: string | null;
  is_active: boolean;
  include_clinical?: boolean;
}

export interface PortalLinkCreated extends PortalLink {
  url: string;
}

export interface PortalAppointment {
  starts_at: string;
  professional_name: string | null;
  treatment_name: string | null;
  status: string;
}

export interface PortalCharge {
  id?: string | null;
  description: string;
  issued_on: string;
  amount: string;
  pending: string;
}

export interface PortalView {
  patient_name: string;
  clinic_name: string;
  upcoming: PortalAppointment[];
  past: PortalAppointment[];
  balance: string;
  charges: PortalCharge[];
  expires_at: string;
  payment_accounts?: {
    label: string;
    qr_data: string | null;
    holder_name: string | null;
    holder_id: string | null;
    account_type: string | null;
    account_number: string | null;
    email: string | null;
    note: string | null;
  }[];
  ortodoncia?: PortalOrtho | null;
  plan?: { treatment: string; fdi_number: string | null; status: string; status_label: string }[];
  odontograma?: { fdi_number: string; surface: string; condition: string }[];
  comparaciones?: { id: string; title: string; treatment: string | null; before_id: string; after_id: string }[];
  comprobantes?: PortalComprobante[];
  incluye_clinica?: boolean;
}

export interface PortalCuota {
  id: string;
  number: number;
  planned_on: string | null;
  attended_on: string | null;
  amount: string;
  paid: string;
  balance: string;
  status: string;
}

export interface PortalOrtho {
  code: string;
  appliance: string | null;
  started_on: string | null;
  estimated_months: number | null;
  status: string;
  controls_attended: number;
  controls_total: number;
  progress: number | null;
  next_control_on: string | null;
  next_control_overdue: boolean;
  agreed_total: string;
  paid: string;
  balance: string;
  cuotas: PortalCuota[];
}

export interface PortalComprobante {
  id: string;
  amount: string;
  paid_on: string;
  destino: string;
  status: 'pendiente' | 'aceptado' | 'rechazado';
  status_label: string;
  reject_reason: string | null;
  created_at: string;
}
