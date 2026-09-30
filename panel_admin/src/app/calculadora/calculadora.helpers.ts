import { AppCarModelPart } from '../vehicles/vehicles.model';
import { ReelCatalogItem } from '../ordenes/ordenes.model';
import {
  COTIZACION_DRAFT_VERSION,
  COTIZACION_STATE_KEY,
  CotizacionDraft,
  CotizacionLine,
  FilmOption,
} from './calculadora.model';

/** Clave de una bobina (lamina + ancho a 2 decimales). Mismo formato que
 * `ProformaFormComponent.reelKey`, para que el borrador coincida con el catalogo. */
export function reelKey(windowFilm: number, width: string | number): string {
  return `${windowFilm}|${Number(width).toFixed(2)}`;
}

/** Filtro de UX (espejo de `business/pricing.py`): la bobina debe ser al menos tan
 * ancha como el item y tener metros suficientes para `largo x cantidad`. El
 * servidor valida de todos modos al crear la proforma. */
export function isReelEligible(reel: ReelCatalogItem, item: AppCarModelPart): boolean {
  const neededMeters = Number(item.length) * Math.max(Number(item.quantity), 1);
  return Number(reel.width) >= Number(item.width) && Number(reel.available_meters) >= neededMeters;
}

/** Laminas elegibles para un item, de la mas barata a la mas cara. */
export function filmOptionsFor(reels: ReelCatalogItem[], item: AppCarModelPart): FilmOption[] {
  return reels
    .filter((reel) => isReelEligible(reel, item))
    .map((reel) => ({
      key: reelKey(reel.window_film, reel.width),
      windowFilm: reel.window_film,
      name: reel.window_film_name,
      width: reel.width,
      unitPrice: reel.unit_price,
      availableMeters: reel.available_meters,
    }))
    .sort((a, b) => Number(a.unitPrice) - Number(b.unitPrice) || a.name.localeCompare(b.name));
}

/** `Bs 2.090` (separador de miles es-BO, hasta 2 decimales). Aislado para poder
 * cambiar el formato en un solo lugar (pendiente de negocio, ver DDR). */
export function formatBs(amount: number): string {
  const value = new Intl.NumberFormat('es-BO', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
    useGrouping: true,
  }).format(amount);
  return `Bs ${value}`;
}

export interface WhatsappLine {
  itemName: string;
  filmName: string;
  subtotal: number;
}

/** Mensaje prearmado de la consulta: vehiculo, items con lamina y total. */
export function buildWhatsappMessage(
  vehicle: string,
  sucursal: string,
  lines: WhatsappLine[],
  total: number
): string {
  const rows = lines.map((l) => `- ${l.itemName}: ${l.filmName} (${formatBs(l.subtotal)})`);
  return [
    'Hola, quiero consultar por una cotizacion de laminas.',
    `Vehiculo: ${vehicle}`,
    `Sucursal: ${sucursal}`,
    ...rows,
    `Total referencial: ${formatBs(total)}`,
  ].join('\n');
}

export function buildWhatsappUrl(number: string, message: string): string {
  const digits = number.replace(/\D/g, '');
  return `https://wa.me/${digits}?text=${encodeURIComponent(message)}`;
}

/** Estado de navegacion que recibe `ProformaFormComponent`. */
export function draftToState(draft: CotizacionDraft): Record<string, CotizacionDraft> {
  return { [COTIZACION_STATE_KEY]: draft };
}

/** Lee y valida el borrador de `history.state`; ante cualquier duda devuelve `null`
 * (el formulario abre vacio, como antes). */
export function parseDraft(state: unknown): CotizacionDraft | null {
  const raw = (state as Record<string, unknown> | null)?.[COTIZACION_STATE_KEY] as
    | Partial<CotizacionDraft>
    | undefined;
  if (!raw || raw.version !== COTIZACION_DRAFT_VERSION) {
    return null;
  }
  if (!Number.isInteger(raw.sucursal) || !Number.isInteger(raw.carModelId) || !Array.isArray(raw.lines)) {
    return null;
  }
  const lines: CotizacionLine[] = [];
  for (const line of raw.lines as Partial<CotizacionLine>[]) {
    if (
      !line ||
      !Number.isInteger(line.carPartId) ||
      !Number.isInteger(line.windowFilm) ||
      !Number.isInteger(line.quantity) ||
      typeof line.width !== 'string' ||
      typeof line.length !== 'string'
    ) {
      return null;
    }
    lines.push({
      carPartId: line.carPartId as number,
      windowFilm: line.windowFilm as number,
      width: line.width,
      length: line.length,
      quantity: line.quantity as number,
    });
  }
  if (lines.length === 0) {
    return null;
  }
  return {
    version: COTIZACION_DRAFT_VERSION,
    sucursal: raw.sucursal as number,
    carModelId: raw.carModelId as number,
    lines,
  };
}
