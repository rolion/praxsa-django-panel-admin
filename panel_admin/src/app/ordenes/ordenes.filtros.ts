/** Utilidades puras de los filtros de los listados de Ordenes (Proformas, Notas de
 * Trabajo y Notas de Venta). El filtrado es del lado del cliente sobre las filas ya
 * cargadas (ver DDR-filtros-busqueda-reportes-filtros-listados-ordenes). Las fechas son
 * locales: se compara solo la parte `YYYY-MM-DD`, sin conversion de zona horaria. */

export interface OpcionFiltro {
  value: string;
  label: string;
}

/** Valor de filtro "sin seleccion" (todos). */
export const TODOS = '';

/** Valor del filtro Cobro de Notas de Trabajo para una nota que aun no tiene nota de venta. */
export const SIN_NOTA_VENTA = 'sin_nota_venta';

/** Estado de la nota de trabajo (filtros "Estado" en Notas de Trabajo y "Trabajo" en Notas de Venta). */
export const TRABAJO_OPTIONS: OpcionFiltro[] = [
  { value: 'en_proceso', label: 'En proceso' },
  { value: 'terminado', label: 'Terminado' },
  { value: 'cancelada', label: 'Cancelada' },
];

/** Estado de la nota de venta (filtro "Cobro"). */
export const COBRO_OPTIONS: OpcionFiltro[] = [
  { value: 'por_cobrar', label: 'Por cobrar' },
  { value: 'pagada', label: 'Pagada' },
  { value: 'anulada', label: 'Anulada' },
];

/** Cobro de Notas de Trabajo: ademas de los estados, las notas sin nota de venta. */
export const COBRO_NOTA_TRABAJO_OPTIONS: OpcionFiltro[] = [
  ...COBRO_OPTIONS,
  { value: SIN_NOTA_VENTA, label: 'Sin nota de venta' },
];

/** Valores unicos, no vacios y ordenados alfabeticamente, para las opciones de un select. */
export function opcionesUnicas<T>(rows: T[], getter: (row: T) => string | null | undefined): string[] {
  const valores = new Set<string>();
  for (const row of rows) {
    const valor = getter(row);
    if (valor) {
      valores.add(valor);
    }
  }
  return Array.from(valores).sort((a, b) => a.localeCompare(b, 'es'));
}

/** Opciones `{value, label}` unicas por valor (ej. sucursal o instalador por id), sin
 * valores vacios y ordenadas por etiqueta. */
export function opcionesPorId<T>(
  rows: T[],
  getId: (row: T) => number | null | undefined,
  getLabel: (row: T) => string | null | undefined
): OpcionFiltro[] {
  const porId = new Map<string, string>();
  for (const row of rows) {
    const id = getId(row);
    if (id !== null && id !== undefined && !porId.has(String(id))) {
      porId.set(String(id), getLabel(row) || `#${id}`);
    }
  }
  return Array.from(porId, ([value, label]) => ({ value, label })).sort((a, b) => a.label.localeCompare(b.label, 'es'));
}

/** Mensaje de error del rango de fechas, o '' si es valido (un extremo vacio es valido). */
export function rangoFechasInvalido(desde: string, hasta: string): string {
  return desde && hasta && desde > hasta ? 'La fecha inicial no puede ser mayor que la final.' : '';
}

/** `fecha` (ISO con o sin hora) dentro del rango inclusivo. Sin rango activo pasa todo;
 * con rango activo una fecha nula no pasa. Un rango invalido no filtra por fecha. */
export function dentroDeRango(fecha: string | null | undefined, desde: string, hasta: string): boolean {
  if ((!desde && !hasta) || rangoFechasInvalido(desde, hasta)) {
    return true;
  }
  if (!fecha) {
    return false;
  }
  const dia = fecha.slice(0, 10);
  return (!desde || dia >= desde) && (!hasta || dia <= hasta);
}

/** Lee el valor de un `<select>`/`<input>` de un evento del DOM. */
export function valorDeEvento(event: Event): string {
  return (event.target as HTMLInputElement | HTMLSelectElement).value;
}
