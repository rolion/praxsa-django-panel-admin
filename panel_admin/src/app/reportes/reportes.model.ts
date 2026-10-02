/** Contratos de los reportes de solo lectura (API `product/reportes/*`, ver
 * ADR-reportes-utilidad-ventas-diarias-calculo-y-api). Los importes viajan como
 * texto decimal ("580.00"), igual que el resto de la API. */

export type ReporteSalesType = 'venta_instalacion' | 'venta_metro_lineal';
export type ReporteTipoPago = 'efec' | 'trans';

export interface ReporteFiltros {
  desde: string; // YYYY-MM-DD
  hasta: string; // YYYY-MM-DD
  /** Un solo id (parametro `sucursal`, se conserva por compatibilidad). */
  sucursal?: number | null;
  /** Varias sucursales (`sucursales=1,2`); vacio = "todas las activas" en el servidor. */
  sucursales?: number[];
  salesType?: ReporteSalesType | '';
  tipoPago?: ReporteTipoPago | '';
}

export interface ResumenVentas {
  ventas: number;
  venta_lamina: string;
  instalacion: string;
  bruto: string;
  descuento: string;
  cobrado: string;
}

interface VentaBase {
  nota_venta_id: number;
  nota_trabajo_id: number;
  proforma_id: number;
  fecha: string;
  cliente: string;
  sales_type: ReporteSalesType;
  sales_type_label: string;
  sucursal_id: number | null;
  sucursal_name: string;
  venta_lamina: string;
  instalacion: string;
  bruto: string;
  descuento: string;
  cobrado: string;
}

// ---- Ventas Diarias (sin costos ni utilidad) ----
export interface VentaDiariaRow extends VentaBase {
  pago_id: number;
  vehiculo: string;
  tipo_pago: ReporteTipoPago;
  tipo_pago_label: string;
  registro_contable: string | null;
  cerrado: boolean;
}

export interface VentasDiariasReport {
  rows: VentaDiariaRow[];
  totales: ResumenVentas;
  por_tipo_venta: (ResumenVentas & { sales_type: ReporteSalesType; label: string })[];
  por_tipo_pago: (ResumenVentas & { tipo_pago: ReporteTipoPago; label: string })[];
  sin_sucursal: boolean;
}

// ---- Utilidad ----
export interface UtilidadVentaRow extends VentaBase {
  costo_compra: string;
  utilidad_antes: string;
  utilidad_despues: string;
  margen: string | null;
  costo_incompleto: boolean;
}

export interface ResumenUtilidad extends ResumenVentas {
  costo_compra: string;
  utilidad_antes: string;
  utilidad_despues: string;
  margen: string | null;
  ventas_costo_incompleto: number;
}

export interface LaminaUtilidadRow {
  sucursal_id: number | null;
  sucursal_name: string;
  window_film_id: number | null;
  window_film_name: string | null;
  width: string;
  metros: string;
  venta_lamina: string;
  costo_compra: string;
  utilidad_antes: string;
}

export interface UtilidadReport {
  ventas: UtilidadVentaRow[];
  por_lamina: LaminaUtilidadRow[];
  totales: ResumenUtilidad;
  por_tipo_venta: (ResumenUtilidad & { sales_type: ReporteSalesType; label: string })[];
  sin_sucursal: boolean;
}
