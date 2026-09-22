export interface Permission {
  id: string;
  code: string;
  module: string;
  description: string;
}

export interface Role {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  permissions: Permission[];
}

export interface RoleCreate {
  name: string;
  description?: string | null;
  permission_codes: string[];
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_superadmin: boolean;
  roles: Role[];
}

export interface UserCreate {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  role_ids: string[];
}

export interface UserUpdate {
  first_name?: string;
  last_name?: string;
  is_active?: boolean;
  role_ids?: string[];
  /** Contraseña temporal nueva; cierra todas sus sesiones abiertas. */
  password?: string;
}
