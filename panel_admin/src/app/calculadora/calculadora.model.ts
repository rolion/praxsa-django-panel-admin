import { AppCarModelPart } from '../vehicles/vehicles.model';

/* Modelos de la pantalla Calculadora de precios. Sucursal, marca, modelo, item y
 * bobina reutilizan los tipos del API que ya existen (`OrdenSucursal`,
 * `AppCarBrand`, `AppCarModel`, `AppCarModelPart`, `ReelCatalogItem`): no se
 * duplican con otro nombre. */

/** Lamina (bobina = lamina + ancho) que se puede elegir para un item. */
export interface FilmOption {
  /** Clave `lamina|ancho` (ancho a 2 decimales), igual que `ProformaFormComponent.reelKey`. */
  key: string;
  windowFilm: number;
  name: string;
  width: string;
  /** Precio por metro de la bobina (string del API). */
  unitPrice: string;
  availableMeters: string;
  /** Reservado para la lamina "Recomendada". Ninguna regla la marca todavia
   * (ADR-pricing-calculator-screen-cotizacion-en-cliente, punto 8). */
  recommended?: boolean;
}

/** Fila de la cotizacion: un item del modelo con su lamina y subtotal. */
export interface QuoteLine {
  item: AppCarModelPart;
  film: FilmOption | null;
  excluded: boolean;
  /** Vista previa, no autoritativa: el servidor recalcula al crear la proforma. */
  subtotal: number;
}

export interface QuoteSummary {
  lines: QuoteLine[];
  /** Suma de los subtotales de los items no excluidos con lamina. */
  total: number;
  /** Items con lamina elegida y no excluidos. */
  pricedCount: number;
}

/** Linea del borrador que viaja a "Crear proforma". */
export interface CotizacionLine {
  carPartId: number;
  windowFilm: number;
  width: string;
  length: string;
  quantity: number;
}

/** Borrador de cotizacion que se pasa al formulario de proforma por
 * `history.state` (clave `cotizacion`). Sin datos del cliente. */
export interface CotizacionDraft {
  version: 1;
  sucursal: number;
  carModelId: number;
  lines: CotizacionLine[];
}

export const COTIZACION_STATE_KEY = 'cotizacion';
export const COTIZACION_DRAFT_VERSION = 1;

/** Valor de una fila del FormArray de items. */
export interface LineFormValue {
  reel: string | null;
  excluded: boolean;
}

export type CalculadoraState = 'initial' | 'loading' | 'empty' | 'error' | 'active';
export type EmptyReason = 'sin-items' | 'sin-stock';
