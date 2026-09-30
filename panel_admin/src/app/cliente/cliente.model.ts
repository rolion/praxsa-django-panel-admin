/* Modelos del flujo de cliente final (ADR-pricing-calculator-screen-registro-y-api-cliente). */

/** Perfil del cliente autenticado (`GET product/client/me`). Vive solo en memoria: no se
 * guarda en `localStorage` (ADR-003, PII). */
export interface ClientProfile {
  name: string;
  lastname: string;
  email: string;
  phone_number: string;
  car_plate: string;
  ci_nit: string;
}

/** Cuerpo de `POST product/client/register`. */
export interface RegisterPayload {
  name: string;
  lastname: string;
  email: string;
  phone_number: string;
  car_plate: string;
  /** Opcional: por defecto el servidor usa el correo. */
  username?: string;
  password: string;
}

/** Fila de `GET product/client/proformas` (solo lectura). */
export interface ClientProformaRow {
  id: number;
  /** ISO 8601. */
  date: string;
  car_brand_name: string;
  car_model_name: string;
  car_plate: string;
  /** Decimal como string. */
  total_price: string;
}

/** Linea de `POST product/invoice`. Los importes son los de la vista previa y el servidor
 * los IGNORA y recalcula (ADR-004): se envian solo porque el serializer los declara. */
export interface InvoiceLinePayload {
  car_part: number;
  width: string;
  length: string;
  quantity: number;
  window_film: number;
  installation_price: string;
  window_film_price: string;
  sub_total: string;
}

/** Cuerpo de `POST product/invoice` (mismo contrato que usa proforma/). */
export interface InvoicePayload {
  name: string;
  email: string;
  car_plate: string;
  car_model_id: number;
  total_price: string;
  phone_number: string;
  /** `null` cuando la cuenta no tiene CI/NIT (el registro no lo pide). */
  ci_nit: string | null;
  sucursal: number;
  carPartItems: InvoiceLinePayload[];
}

export type AccesoMode = 'login' | 'register';
