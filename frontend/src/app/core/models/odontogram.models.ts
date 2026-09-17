export type ToothSurface = 'whole' | 'mesial' | 'distal' | 'vestibular' | 'lingual' | 'oclusal';

export interface ToothCondition {
  id?: string;
  fdi_number: string;
  surface: ToothSurface;
  condition: string;
  notes?: string | null;
}

export interface Odontogram {
  id: string;
  patient_id: string;
  professional_id: string | null;
  created_by_id: string | null;
  created_at: string;
  previous_odontogram_id: string | null;
  notes: string | null;
  type: 'initial' | 'followup';
  conditions: ToothCondition[];
}

export interface OdontogramSummary {
  id: string;
  created_at: string;
  type: 'initial' | 'followup';
}

export interface OdontogramCreate {
  professional_id?: string | null;
  notes?: string | null;
  conditions: ToothCondition[];
}
