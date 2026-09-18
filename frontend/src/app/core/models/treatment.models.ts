export interface Treatment {
  id: string;
  name: string;
  description: string | null;
  default_price: number;
  is_active: boolean;
}

export interface TreatmentCreate {
  name: string;
  description?: string | null;
  default_price: number;
}

export interface Diagnosis {
  id: string;
  patient_id: string;
  professional_id: string | null;
  created_by_id: string | null;
  created_at: string;
  fdi_number: string | null;
  description: string;
  notes: string | null;
}

export interface DiagnosisCreate {
  fdi_number?: string | null;
  description: string;
  notes?: string | null;
}

export type TreatmentPlanItemStatus =
  | 'propuesto'
  | 'aprobado'
  | 'en_progreso'
  | 'completado'
  | 'cancelado'
  | 'rechazado';

export interface TreatmentPlanItem {
  id: string;
  plan_id: string;
  treatment_id: string;
  treatment_name: string;
  diagnosis_id: string | null;
  professional_id: string | null;
  fdi_number: string | null;
  surface: string | null;
  price: number;
  discount: number;
  net_price: number;
  status: TreatmentPlanItemStatus;
  estimated_date: string | null;
  completed_date: string | null;
  notes: string | null;
}

export interface TreatmentPlanItemCreate {
  treatment_id: string;
  diagnosis_id?: string | null;
  fdi_number?: string | null;
  surface?: string | null;
  price: number;
  discount?: number;
  status?: TreatmentPlanItemStatus;
  notes?: string | null;
}

export interface TreatmentPlan {
  id: string;
  patient_id: string;
  created_by_id: string | null;
  title: string;
  notes: string | null;
  items: TreatmentPlanItem[];
  progress_percent: number;
  total_price: number;
}

export interface TreatmentPlanCreate {
  title: string;
  notes?: string | null;
  items: TreatmentPlanItemCreate[];
}

export type BudgetStatus = 'borrador' | 'enviado' | 'visto' | 'aceptado' | 'rechazado';

export interface BudgetItem {
  id: string;
  treatment_plan_item_id: string | null;
  description: string;
  price: number;
  discount: number;
  quantity: number;
  net_price: number;
}

export interface Budget {
  id: string;
  patient_id: string;
  treatment_plan_id: string;
  created_by_id: string | null;
  created_at: string;
  status: BudgetStatus;
  tax_rate: number;
  notes: string | null;
  responded_at: string | null;
  items: BudgetItem[];
  subtotal: number;
  tax_amount: number;
  total: number;
}

export interface BudgetCreate {
  treatment_plan_id: string;
  tax_rate?: number;
  notes?: string | null;
}
