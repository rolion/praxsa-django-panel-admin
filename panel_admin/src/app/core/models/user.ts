export class User {
  id!: number;
  username!: string;
  firstName!: string;
  lastName!: string;
  token!: string;
  isStaff!: boolean;
  groups!: string[];
  /** Permisos Django efectivos (`app_label.codename`). Ausente en sesiones
   * guardadas antes de que el login los devolviera. */
  permissions?: string[];
}
