import { PaymentMethodCode } from './finance.models';

export type OrthoStatus = 'activo' | 'retencion' | 'pausa' | 'finalizado' | 'abandono';
export type OrthoTad = 'por_confirmar' | 'si' | 'no';
export type OrthoDocStatus = 'por_revisar' | 'pendiente' | 'listo' | 'no_requiere';
export type OrthoDocField = 'doc_xrays' | 'doc_photos' | 'doc_models' | 'doc_folder';
export type OrthoControlStatus = 'pendiente' | 'parcial' | 'pagada' | 'vencida' | 'sin_valor';

export interface Option<T extends string = string> {
  code: T;
  label: string;
}

export interface OrthoOptions {
  statuses: Option<OrthoStatus>[];
  tad: Option<OrthoTad>[];
  doc_statuses: Option<OrthoDocStatus>[];
  doc_fields: Option<OrthoDocField>[];
  appliances: string[];
  stages: string[];
}

export interface OrthoPaymentLine {
  id: string;
  amount: string;
  method: PaymentMethodCode;
  reference: string | null;
  received_on: string;
  notes: string | null;
  voided_at: string | null;
  void_reason: string | null;
}

export interface OrthoControl {
  id: string;
  number: number;
  planned_on: string | null;
  attended_on: string | null;
  planning: string | null;
  arches: string | null;
  elastics: string | null;
  tads: string | null;
  due_on: string | null;
  amount: string;
  notes: string | null;
  paid: string;
  balance: string;
  status: OrthoControlStatus;
  payments: OrthoPaymentLine[];
}

export interface OrthoCase {
  id: string;
  number: number;
  code: string;
  patient: {
    id: string;
    first_name: string;
    last_name: string;
    national_id: string | null;
    phone: string | null;
    whatsapp: string | null;
  };
  professional_id: string | null;
  professional_name: string | null;
  charge_id: string | null;
  status: OrthoStatus;
  stage: string | null;
  needs_review: boolean;
  has_tad: OrthoTad;
  appliance: string | null;
  started_on: string | null;
  estimated_months: number | null;
  agreed_total: string;
  special_attention: boolean;
  special_attention_note: string | null;
  doc_xrays: OrthoDocStatus;
  doc_photos: OrthoDocStatus;
  doc_models: OrthoDocStatus;
  doc_folder: OrthoDocStatus;
  doc_notes: Partial<Record<OrthoDocField, string>>;
  notes: string | null;
  paid: string;
  balance: string;
  controls_total: string;
  difference: string;
  controls_count: number;
  controls_paid: number;
  last_control_on: string | null;
  next_control_on: string | null;
  next_control_overdue: boolean;
  docs_pending: number;
}

export interface OrthoCaseDetail extends OrthoCase {
  controls: OrthoControl[];
  unassigned_paid: string;
}

export interface OrthoCaseList {
  items: OrthoCase[];
  total: number;
  active: number;
  inactive: number;
}

export type OrthoCaseFields = Partial<
  Pick<
    OrthoCase,
    | 'professional_id'
    | 'status'
    | 'stage'
    | 'needs_review'
    | 'has_tad'
    | 'appliance'
    | 'started_on'
    | 'estimated_months'
    | 'agreed_total'
    | 'special_attention'
    | 'special_attention_note'
    | OrthoDocField
    | 'doc_notes'
    | 'notes'
  >
>;

export type OrthoControlFields = Partial<
  Pick<OrthoControl, 'planned_on' | 'attended_on' | 'planning' | 'arches' | 'elastics' | 'tads' | 'due_on' | 'amount' | 'notes'>
>;

export interface OrthoFilters {
  q?: string;
  status?: string;
  has_tad?: string;
  docs?: string;
  next_control?: string;
  special_attention?: string;
  needs_review?: string;
  professional_id?: string;
}

export const ORTHO_STATUS_LABEL: Record<OrthoStatus, string> = {
  activo: 'Activo',
  retencion: 'En retención',
  pausa: 'En pausa',
  finalizado: 'Finalizado',
  abandono: 'Abandonó',
};

export const ORTHO_TAD_LABEL: Record<OrthoTad, string> = { por_confirmar: 'Por confirmar', si: 'Sí', no: 'No' };

export const ORTHO_DOC_LABEL: Record<OrthoDocStatus, string> = {
  por_revisar: 'Por revisar',
  pendiente: 'Pendiente',
  listo: 'Listo',
  no_requiere: 'No requiere',
};

export const ORTHO_DOC_FIELDS: { code: OrthoDocField; label: string; icon: string }[] = [
  { code: 'doc_xrays', label: 'Radiografías', icon: 'filter_b_and_w' },
  { code: 'doc_photos', label: 'Fotografías', icon: 'photo_camera' },
  { code: 'doc_models', label: 'Modelos', icon: 'view_in_ar' },
  { code: 'doc_folder', label: 'Carpeta clínica', icon: 'folder_shared' },
];

export const ORTHO_CONTROL_LABEL: Record<OrthoControlStatus, string> = {
  pendiente: 'Pendiente',
  parcial: 'Parcial',
  pagada: 'Pagada',
  vencida: 'Vencida',
  sin_valor: 'Sin valor',
};

export function orthoCode(n: number): string {
  return `ORT-${String(n).padStart(4, '0')}`;
}
