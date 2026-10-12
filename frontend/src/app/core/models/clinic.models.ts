export interface Clinic {
  id: string;
  name: string;
  legal_name: string | null;
  tax_id: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  logo_url: string | null;
  primary_color: string | null;
  secondary_color: string | null;
  timezone: string;
  currency: string;
  practice_type: 'independiente' | 'consultorio' | 'clinica';
  logo_data: string | null;
  slogan: string | null;
  document_footer: string | null;
  opens_at: string;
  closes_at: string;
  work_days: string;
  hidden_modules: string[];
  setup_completed_at: string | null;
  legal_rep_name: string | null;
  legal_rep_id: string | null;
  dpo_name: string | null;
  dpo_email: string | null;
  health_permit_number: string | null;
  health_permit_expires_on: string | null;
  tax_regime: string;
  keeps_accounting: boolean;
  special_taxpayer: string | null;
  sri_establishment: string;
  sri_emission_point: string;
  vat_rate: string;
  record_retention_years: number;
  privacy_extra: string | null;
  session_timeout_minutes: number;
  terms_version: string | null;
  terms_accepted_at: string | null;
  terms_accepted_by: string | null;
  terms_current_version: string;
}

export interface Specialty {
  id: string;
  name: string;
}

export interface Professional {
  id: string;
  first_name: string;
  last_name: string;
  specialty_id: string | null;
  license_number: string | null;
  color_hex: string;
  is_active: boolean;
}

export interface ProfessionalCreate {
  first_name: string;
  last_name: string;
  specialty_id?: string | null;
  license_number?: string | null;
  color_hex?: string;
}

export interface ProfessionalUpdate {
  first_name?: string;
  last_name?: string;
  specialty_id?: string | null;
  license_number?: string | null;
  color_hex?: string;
  is_active?: boolean;
}

export interface Branch {
  id: string;
  name: string;
  address: string | null;
  phone: string | null;
  is_main: boolean;
}

export interface Operatory {
  id: string;
  branch_id: string;
  name: string;
  is_active: boolean;
}
