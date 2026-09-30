export type SalesType = 'venta_instalacion' | 'venta_metro_lineal';
/** Estado GLOBAL de la orden (derivado en el servidor). 'finalizado' = trabajo terminado y pagado. */
export type ProformaStatus = 'proforma' | 'en_trabajo' | 'por_cobrar' | 'finalizado' | 'anulada';
export type NotaTrabajoStatus = 'en_proceso' | 'terminado' | 'cancelada';
export type NotaVentaStatus = 'por_cobrar' | 'pagada' | 'anulada';
export type TipoPago = 'efec' | 'trans';

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
  nota_venta_id: number | null;
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
  /** Ausente si el backend aun no lo expone (la marca queda vacia en el filtro). */
  car_brand_name?: string | null;
  car_plate: string | null;
  instaladar: number | null;
  instalador_name: string | null;
  codigo_garantia: string | null;
  entrada_vehiculo: string | null;
  salida_vehiculo: string | null;
  sucursal_id: number | null;
  sucursal_name: string | null;
  is_close: boolean;
  status: NotaTrabajoStatus;
  status_label: string;
  nota_venta: { id: number; status: NotaVentaStatus; status_label: string; total_price: string } | null;
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

export interface AppPago {
  id: number;
  monto: string;
  tipo_pago: TipoPago;
  tipo_pago_label: string;
  registro_contable: string | null;
  created_on: string;
  cerrado: boolean;
}

/** Fila del listado de notas de venta. */
export interface AppNotaVenta {
  id: number;
  nota_trabajo_id: number;
  proforma_id: number | null;
  name: string;
  ci_nit: string | null;
  total_price: string;
  created_on: string | null;
  status: NotaVentaStatus;
  status_label: string;
  work_status: NotaTrabajoStatus;
  work_status_label: string;
  sucursal_id: number | null;
  sucursal_name: string | null;
}

export interface AppNotaVentaDetail extends AppNotaVenta {
  pago: AppPago | null;
  car_plate: string | null;
  sales_type_label: string | null;
}

/** Lo unico que se envia al registrar un pago: el monto lo fija el servidor. */
export interface PagoPayload {
  tipo_pago: TipoPago;
  registro_contable: string;
}
