export interface ClinicalEvolution {
  id: string;
  patient_id: string;
  appointment_id: string | null;
  professional_id: string | null;
  created_by_id: string | null;
  created_at: string;
  procedure: string;
  fdi_numbers: string | null;
  anesthesia: string | null;
  materials: string | null;
  diagnosis: string | null;
  evolution: string | null;
  instructions: string | null;
  next_appointment_notes: string | null;
  voided_at?: string | null;
  void_reason?: string | null;
}

export interface EvolutionCreate {
  appointment_id?: string | null;
  procedure: string;
  fdi_numbers?: string | null;
  anesthesia?: string | null;
  materials?: string | null;
  diagnosis?: string | null;
  evolution?: string | null;
  instructions?: string | null;
  next_appointment_notes?: string | null;
}

export interface PrescriptionItem {
  id?: string;
  medication: string;
  dosage?: string | null;
  frequency?: string | null;
  duration?: string | null;
  instructions?: string | null;
}

export interface Prescription {
  id: string;
  patient_id: string;
  professional_id: string | null;
  created_at: string;
  notes: string | null;
  items: PrescriptionItem[];
  voided_at?: string | null;
  void_reason?: string | null;
}

export interface PrescriptionCreate {
  /** Obligatorio: quien firma la receta. */
  professional_id: string;
  notes?: string | null;
  items: PrescriptionItem[];
}

export interface ConsentTemplate {
  id: string;
  name: string;
  procedure_type: string | null;
  body: string;
  is_active: boolean;
}

export interface Consent {
  id: string;
  patient_id: string;
  template_id: string | null;
  created_at: string;
  title: string;
  procedure_type: string | null;
  body: string;
  status: 'pendiente' | 'firmado';
  signed_at: string | null;
  signed_by_name: string | null;
  signature_notes: string | null;
  professional_id?: string | null;
  tooth?: string | null;
  signer_id_number?: string | null;
  signer_relationship?: string | null;
  signature_image?: string | null;
  professional_signature_image?: string | null;
  witness_name?: string | null;
  signed_channel?: 'presencial' | 'remoto' | null;
  signed_ip?: string | null;
  content_hash?: string | null;
  sign_token_expires_at?: string | null;
  sign_link_sent_at?: string | null;
  voided_at?: string | null;
  void_reason?: string | null;
}

export interface ConsentCreate {
  template_id?: string | null;
  professional_id?: string | null;
  title?: string | null;
  procedure_type?: string | null;
  body?: string | null;
  tooth?: string | null;
  notes?: string | null;
}

export interface ConsentSignPayload {
  signed_by_name: string;
  signer_id_number?: string | null;
  signer_relationship?: string | null;
  signature_image?: string | null;
  professional_signature_image?: string | null;
  witness_name?: string | null;
  signature_notes?: string | null;
}

export interface ConsentSignLink {
  url: string;
  expires_at: string;
  emailed: boolean;
  email_error: string | null;
}

export interface ConsentLibraryItem {
  name: string;
  procedure_type: string;
  preview: string;
  added: boolean;
}

export interface PublicConsentView {
  clinic_name: string;
  clinic_logo: string | null;
  clinic_color: string | null;
  patient_name: string;
  title: string;
  body: string;
  expires_at: string;
}

export interface PatientDocument {
  id: string;
  patient_id: string;
  created_at: string;
  document_type: string;
  title: string;
  description: string | null;
  original_filename: string;
  mime_type: string | null;
  size_bytes: number | null;
  archived_at?: string | null;
  archived_reason?: string | null;
}

export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  consentimiento: 'Consentimiento informado',
  historia: 'Historia clínica',
  presupuesto: 'Presupuesto',
  receta: 'Receta',
  radiografia: 'Radiografía',
  informe: 'Informe',
  otro: 'Documento',
};
