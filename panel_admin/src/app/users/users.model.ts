export interface AppUser {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_staff: boolean;
  phone_number: string | null;
  groups: number[];
  sucursales: number[];
}

export interface AppGroup {
  id: number;
  name: string;
  permissions: number[];
}

export interface AppPermission {
  id: number;
  name: string;
  codename: string;
  app_label: string;
}

export interface AppInstalador {
  id: number;
  name: string;
  address: string;
  phonenumber: string;
  sucursal: number[];
  sucursal_names: string[];
  is_active: boolean;
}

export interface InstaladorPayload {
  name: string;
  address: string;
  phonenumber: string;
  sucursal: number[];
}

export interface AppSucursal {
  id: number;
  name: string;
  address: string;
  phone_number: string | null;
  enable_to_install_windows_film: boolean;
}

export interface CreateUserPayload {
  username: string;
  password: string;
  password_confirm: string;
  is_active: boolean;
  first_name: string;
  last_name: string;
  email: string;
  phone_number: string | null;
  sucursales: number[];
  groups: number[];
}
