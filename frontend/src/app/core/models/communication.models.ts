export type MessageChannel = 'whatsapp' | 'sms' | 'email';

/** `simulado` is deliberately distinct from `enviado`: the backend refuses to
 *  collapse them, and so does the UI. */
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

// ---- Assistant ----------------------------------------------------------

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
  /** Exactly what the assistant was given — shown so a clinician can check
   *  its whole world before trusting a word of the output. */
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

// ---- Portal -------------------------------------------------------------

export interface PortalLink {
  id: string;
  patient_id: string;
  expires_at: string;
  created_at: string;
  last_used_at: string | null;
  use_count: number;
  revoked_at: string | null;
  is_active: boolean;
}

/** The raw URL comes back exactly once, at creation. Only its hash is stored,
 *  so it can never be shown again. */
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
}
