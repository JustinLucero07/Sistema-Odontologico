export type LabOrderStatus =
  | 'borrador'
  | 'enviado'
  | 'en_proceso'
  | 'recibido'
  | 'probado'
  | 'instalado'
  | 'rechazado'
  | 'cancelado';

export interface LabCatalogEntry {
  code: string;
  label: string;
}

export interface LabCatalog {
  statuses: LabCatalogEntry[];
  work_types: LabCatalogEntry[];
}

export interface Laboratory {
  id: string;
  name: string;
  contact_name: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  default_turnaround_days: number | null;
  notes: string | null;
  is_active: boolean;
}

export interface LabOrderEvent {
  id: string;
  status: LabOrderStatus;
  note: string | null;
  created_by_id: string | null;
  created_at: string;
}

export interface LabOrder {
  id: string;
  patient_id: string;
  patient_name: string | null;
  laboratory_id: string;
  laboratory_name: string | null;
  professional_id: string | null;
  treatment_plan_item_id: string | null;
  work_type: string;
  description: string;
  fdi_numbers: string[] | null;
  shade: string | null;
  material: string | null;
  status: LabOrderStatus;
  sent_on: string | null;
  due_on: string | null;
  received_on: string | null;
  cost: string | null;
  notes: string | null;
  created_at: string;
  events: LabOrderEvent[];
  /** Derived server-side; null unless the case is open and past its date. */
  days_overdue: number | null;
}

/** The forward chain, used to offer only the steps a case can actually take. */
export const LAB_STATUS_ORDER: LabOrderStatus[] = [
  'borrador',
  'enviado',
  'en_proceso',
  'recibido',
  'probado',
  'instalado',
];

export const LAB_TERMINAL: LabOrderStatus[] = ['instalado', 'cancelado'];

export function nextStatuses(current: LabOrderStatus): LabOrderStatus[] {
  if (LAB_TERMINAL.includes(current)) return [];
  const index = LAB_STATUS_ORDER.indexOf(current);
  // From "rechazado" the case goes back out to the lab, so the chain restarts
  // at "enviado" rather than at whatever step it had reached.
  const forward = index < 0 ? LAB_STATUS_ORDER.slice(1) : LAB_STATUS_ORDER.slice(index + 1);
  return [...forward, 'rechazado', 'cancelado'];
}
