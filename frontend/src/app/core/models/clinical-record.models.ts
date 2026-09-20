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
}

export interface PrescriptionCreate {
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
}

export interface ConsentCreate {
  template_id?: string | null;
  title?: string | null;
  procedure_type?: string | null;
  body?: string | null;
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
