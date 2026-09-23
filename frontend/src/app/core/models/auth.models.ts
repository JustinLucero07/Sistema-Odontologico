export interface LoginRequest {
  email: string;
  password: string;
}

export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
}

export interface CurrentUser {
  id: string;
  clinic_id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_superadmin: boolean;
  roles: string[];
  permissions: string[];
  /** Falta aceptar la versión vigente del acuerdo de confidencialidad. */
  confidentiality_required?: boolean;
}
