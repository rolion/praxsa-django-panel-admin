export type SalesType = 'venta_instalacion' | 'venta_metro_lineal';
export type ProformaStatus = 'proforma' | 'nota_trabajo' | 'por_cobrar' | 'finalizado';

export const SALES_TYPE_INSTALACION: SalesType = 'venta_instalacion';
export const SALES_TYPE_METRO_LINEAL: SalesType = 'venta_metro_lineal';

/** Linea de proforma tal como la devuelve el servidor (importes ya calculados). */
export interface AppProformaLine {
  id: number;
  car_part: number | null;
  car_part_name: string | null;
  window_film: number;
  window_film_name: string;
  width: string;
  length: string;
  quantity: number;
  window_film_price: string;
  installation_price: string;
  sub_total: string;
}

/** Fila del listado de proformas. */
export interface AppProforma {
  id: number;
  sales_type: SalesType;
  sales_type_label: string;
  name: string;
  sucursal: number | null;
  sucursal_name: string | null;
  car_model_name: string | null;
  car_brand_name: string | null;
  car_plate: string | null;
  total_price: string;
  discount: string;
  total_a_pagar: string;
  proforma_created_on: string;
  status: ProformaStatus;
  status_label: string;
  is_close: boolean;
  nota_trabajo_id: number | null;
}

export interface AppProformaDetail extends AppProforma {
  email: string | null;
  ci_nit: string | null;
  phone_number: string;
  car_model_id: number | null;
  discount_reason: string | null;
  items: AppProformaLine[];
}

/** Lo unico que se envia por linea: el servidor calcula precios y subtotales. */
export interface ProformaLinePayload {
  car_part?: number | null;
  window_film: number;
  width: string;
  length: string;
  quantity?: number;
}

export interface ProformaPayload {
  sales_type?: SalesType;
  sucursal?: number;
  name: string;
  email: string;
  ci_nit: string;
  phone_number: string;
  car_plate: string;
  car_model_id: number | null;
  discount: string;
  discount_reason: string;
  items: ProformaLinePayload[];
}

export interface AppNotaTrabajo {
  id: number;
  proforma_id: number;
  name: string;
  car_model_name: string | null;
  car_plate: string | null;
  instaladar: number | null;
  instalador_name: string | null;
  codigo_garantia: string | null;
  entrada_vehiculo: string | null;
  salida_vehiculo: string | null;
  sucursal_id: number | null;
  sucursal_name: string | null;
  is_close: boolean;
  is_finalizada: boolean;
}

export interface AppNotaTrabajoDetail extends AppNotaTrabajo {
  observaciones: string | null;
  responsable_name: string | null;
  sales_type: SalesType | null;
  sales_type_label: string | null;
  resumen: { window_film_name: string | null; width: string; length: string }[];
  proforma_items: AppProformaLine[];
}

export interface NotaTrabajoUpdatePayload {
  instaladar: number | null;
  codigo_garantia: string;
  salida_vehiculo: string | null;
  observaciones: string;
}

/** Bobina (lamina + ancho) con stock en una sucursal. */
export interface ReelCatalogItem {
  window_film: number;
  window_film_name: string;
  width: string;
  available_meters: string;
  unit_price: string;
}

export interface OrdenSucursal {
  id: number;
  name: string;
  address: string;
}

export interface OrdenInstalador {
  id: number;
  name: string;
}
