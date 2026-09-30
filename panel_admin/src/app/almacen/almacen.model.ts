export interface AppWindowFilm {
  id: number;
  name: string;
  description: string;
  content: string | null;
  image: string | null;
  is_active: boolean;
}

export interface AppWindowFilmReel {
  id: number;
  window_film: number;
  window_film_name: string;
  width: string;
  length: string;
  price: string;
  is_active: boolean;
}

export interface AppInventario {
  id: number;
  sucursal: number;
  sucursal_name: string;
  bobina: number;
  window_film_name: string;
  bobina_width: string;
  quantity: number;
  to_install: string;
  installed: string;
  original_length: string;
  date: string;
  numero_referencia: number;
  precio_compra_mtr_lineal: string;
  precio_venta_mtr_lineal: string;
  nro_lote: string | null;
  is_active: boolean;
}

export interface InventarioUpdatePayload {
  to_install?: string;
  installed?: string;
  precio_compra_mtr_lineal?: string;
  precio_venta_mtr_lineal?: string;
  nro_lote?: string | null;
}

/** Alta manual de Inventario -- campos obligatorios vs. opcionales segun
 * ADR-modulo-almacen-modelo-datos-imagen-soft-delete (seccion
 * Actualizacion). Los opcionales, si se omiten, toman el default de
 * servidor (installed=0, original_length=to_install, date=ahora). */
export interface InventarioCreatePayload {
  sucursal: number;
  bobina: number;
  quantity: number;
  to_install: string;
  precio_compra_mtr_lineal: string;
  precio_venta_mtr_lineal: string;
  installed?: string;
  original_length?: string;
  date?: string;
  numero_referencia?: number;
  nro_lote?: string | null;
}

export interface AppPrecioSucursal {
  id: number;
  sucursal: number;
  sucursal_name: string;
  lamina: number;
  lamina_name: string;
  width: string;
  precio_venta: string;
}

export interface PrecioSucursalPayload {
  sucursal: number;
  lamina: number;
  width: string;
  precio_venta: string;
}

export interface AppSucursal {
  id: number;
  name: string;
}
