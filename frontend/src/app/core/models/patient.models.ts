export type Sex = 'M' | 'F' | 'O';

export interface PatientListItem {
  id: string;
  first_name: string;
  last_name: string;
  national_id: string | null;
  age: number | null;
  phone: string | null;
  whatsapp: string | null;
}

export interface Patient {
  id: string;
  first_name: string;
  last_name: string;
  national_id: string | null;
  birth_date: string | null;
  age: number | null;
  sex: Sex | null;
  phone: string | null;
  whatsapp: string | null;
  email: string | null;
  address: string | null;
  city: string | null;
  occupation: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  photo_url: string | null;
  notes: string | null;
}

export interface PatientCreate {
  first_name: string;
  last_name: string;
  national_id?: string | null;
  birth_date?: string | null;
  sex?: Sex | null;
  phone?: string | null;
  whatsapp?: string | null;
  email?: string | null;
  address?: string | null;
  city?: string | null;
  occupation?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  notes?: string | null;
}

export type PatientUpdate = Partial<PatientCreate>;

export interface MedicalHistory {
  id: string;
  patient_id: string;
  created_by_id: string | null;
  created_at: string;

  allergies: string | null;
  medications: string | null;
  medical_conditions: string | null;
  surgeries: string | null;
  habits: string | null;
  is_pregnant: boolean | null;
  vital_signs: string | null;

  chief_complaint: string | null;
  present_illness_history: string | null;
  oral_hygiene: string | null;
  dental_habits: string | null;
  dental_history: string | null;

  extraoral_exam: string | null;
  intraoral_exam: string | null;
  soft_tissues: string | null;
  gums: string | null;
  periodontium: string | null;
  tmj: string | null;
  occlusion: string | null;

  observations: string | null;
}

export type MedicalHistoryCreate = Partial<
  Omit<MedicalHistory, 'id' | 'patient_id' | 'created_by_id' | 'created_at'>
>;
