import { SALES_TYPE_INSTALACION, SalesType } from './ordenes.model';

/** Redondeo a 2 decimales (mitad hacia arriba) para la VISTA PREVIA de
 * importes. No es autoritativo: el servidor recalcula y devuelve el valor
 * definitivo (ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo). */
export function round2(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

/** Misma formula que el servidor (business/pricing.py):
 * - instalacion: largo x cantidad x precio lamina + precio instalacion x cantidad
 * - metro lineal: metros x precio lamina */
export function previewSubtotal(
  salesType: SalesType,
  length: number,
  quantity: number,
  unitPrice: number,
  installationPrice: number
): number {
  if (![length, unitPrice].every(Number.isFinite) || length <= 0) {
    return 0;
  }
  if (salesType === SALES_TYPE_INSTALACION) {
    if (!Number.isFinite(quantity) || quantity < 1) {
      return 0;
    }
    return round2(length * quantity * unitPrice + (installationPrice || 0) * quantity);
  }
  return round2(length * unitPrice);
}
