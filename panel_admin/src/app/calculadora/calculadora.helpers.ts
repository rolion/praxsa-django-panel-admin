import { AppCarModelPart } from '../vehicles/vehicles.model';
import { ReelCatalogItem } from '../ordenes/ordenes.model';
import {
  CalcCatalog,
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

// ---- adaptadores del catalogo publico (calculator_info / model_parts / get_inventory) ----

/** Respuesta de `GET product/calculator_info`. */
export interface PublicCalculatorInfo {
  brands?: { id: number; name: string }[];
  models?: { id: number; name: string; brand_id: number; image?: string | null }[];
  sucursales?: { id: number; name: string; addres?: string }[];
}

/** Respuesta de `GET product/model_parts/<id>`. `width`/`length` llegan como string decimal
 * e `installation_price` como float; se normalizan a string con 2 decimales (vista previa,
 * nunca autoritativo). */
export interface PublicModelPartsResponse {
  car_parts?: {
    id: number;
    width: string | number;
    length: string | number;
    quantity: number;
    part_id: number;
    part_name: string;
    installation_price: number | string;
  }[];
}

/** Respuesta de `GET product/get_inventory/<sucursal>/0/0` (todas las bobinas con stock). */
export interface PublicInventoryResponse {
  inventario?: {
    bobina_film_id: number;
    bobina_film_name: string;
    bobina_width: string | number;
    bobina_metros_disponibles: number | string;
    bobina_price: number | string;
  }[];
}

const money = (value: number | string): string => Number(value).toFixed(2);

export function mapCatalog(raw: PublicCalculatorInfo): CalcCatalog {
  const brands = (raw.brands ?? []).map((b) => ({ id: b.id, name: b.name }));
  const brandName = new Map(brands.map((b) => [b.id, b.name]));
  return {
    sucursales: (raw.sucursales ?? []).map((s) => ({ id: s.id, name: s.name, address: s.addres ?? '' })),
    brands,
    models: (raw.models ?? []).map((m) => ({
      id: m.id,
      name: m.name,
      brand_id: m.brand_id,
      brand_name: brandName.get(m.brand_id) ?? '',
      image: m.image ?? null,
    })),
  };
}

export function mapModelParts(raw: PublicModelPartsResponse): AppCarModelPart[] {
  return (raw.car_parts ?? []).map((p) => ({
    id: p.id,
    car_part_id: p.part_id,
    car_part_name: p.part_name,
    width: money(p.width),
    length: money(p.length),
    quantity: p.quantity,
    installation_price: money(p.installation_price),
  }));
}

export function mapInventory(raw: PublicInventoryResponse): ReelCatalogItem[] {
  return (raw.inventario ?? []).map((r) => ({
    window_film: r.bobina_film_id,
    window_film_name: r.bobina_film_name,
    width: money(r.bobina_width),
    available_meters: money(r.bobina_metros_disponibles),
    unit_price: money(r.bobina_price),
  }));
}
