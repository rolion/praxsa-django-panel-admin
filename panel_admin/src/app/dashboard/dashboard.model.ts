/** Contratos de la API del dashboard (`product/dashboard/*`, ver
 * ADR-dashboard-taller-laminas-api-agregados-alcance). Los importes y metros viajan como
 * texto decimal ("580.00"); un bloque `null` significa que el usuario no tiene permiso
 * (distinto de "sin datos", que llega con ceros o listas vacias). */
import { AppProforma } from '../ordenes/ordenes.model';

export interface DashboardBase {
  generado: string;
  sucursal: number | null;
}

export interface KpiVentas {
  mes: string;
  mes_anterior: string;
  variacion: string | null;
}

export interface KpiProformasActivas {
  monto: string;
  cantidad: number;
}

export interface KpiConversion {
  convertidas: number;
  emitidas: number;
  porcentaje: string | null;
}

export interface KpiInstalaciones {
  en_taller: number;
  terminadas_hoy: number;
}

export interface DashboardKpis extends DashboardBase {
  ventas: KpiVentas | null;
  proformas_activas: KpiProformasActivas;
  conversion: KpiConversion;
  instalaciones: KpiInstalaciones;
  sin_sucursal: boolean;
}

export interface ProformasVsVentas extends DashboardBase {
  meses: string[];
  cotizado: string[];
  vendido: string[] | null;
}

export interface SerieMetros {
  nombre: string;
  metros: string[];
  total: string;
}

export interface ConsumoLaminas extends DashboardBase {
  meses: string[];
  series: SerieMetros[];
}

export interface ItemSolicitado {
  nombre: string;
  cantidad: number;
}

export interface ItemsSolicitados extends DashboardBase {
  total: number;
  items: ItemSolicitado[];
}

export type StockEstado = 'ok' | 'bajo' | 'critico';

export interface StockFila {
  sucursal_id: number;
  sucursal: string;
  lamina_id: number;
  lamina: string;
  ancho: string;
  metros: string;
  rollos: number;
  estado: StockEstado;
}

export interface StockCritico extends DashboardBase {
  contadores: { criticos: number; bajos: number; ok: number };
  umbrales: { critico: string; bajo: string };
  filas: StockFila[];
}

export interface ColaFila {
  nota_trabajo_id: number;
  proforma_id: number;
  cliente: string;
  modelo: string | null;
  placa: string | null;
  laminas: string[];
  status: string;
  status_label: string;
  instalador: string | null;
  entrada_vehiculo: string | null;
}

export interface ColaTaller extends DashboardBase {
  total: number;
  filas: ColaFila[];
}

export interface ProformasRecientes extends DashboardBase {
  proformas: AppProforma[];
}

/** Parametros opcionales; solo se envian los que tienen valor y aplican al endpoint. */
export interface DashboardParams {
  sucursal?: number | null;
  meses?: number;
  todos?: boolean;
}
