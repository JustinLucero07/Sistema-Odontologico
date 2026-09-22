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
