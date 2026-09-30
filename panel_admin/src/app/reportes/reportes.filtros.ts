/** Utilidades de fechas e importes de las pantallas de reportes. Las fechas son
 * locales (el servidor usa America/La_Paz sin conversion de zona horaria). */

export const MAX_DIAS_RANGO = 366;

export function toIso(date: Date): string {
  const mes = String(date.getMonth() + 1).padStart(2, '0');
  const dia = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${mes}-${dia}`;
}

export function hoyIso(now: Date = new Date()): string {
  return toIso(now);
}

export function inicioMesIso(now: Date = new Date()): string {
  return toIso(new Date(now.getFullYear(), now.getMonth(), 1));
}

/** Mensaje de error del rango, o '' si es valido (mismas reglas que el servidor). */
export function rangoInvalido(desde: string, hasta: string): string {
  if (!desde || !hasta) {
    return 'Indique la fecha inicial y la final.';
  }
  if (desde > hasta) {
    return 'La fecha inicial no puede ser mayor que la final.';
  }
  const dias = Math.round((Date.parse(hasta) - Date.parse(desde)) / 86_400_000) + 1;
  return dias > MAX_DIAS_RANGO ? `El rango no puede superar ${MAX_DIAS_RANGO} días.` : '';
}

/** Importe con la moneda, igual que las demas tablas del panel ("340.00 Bs"). */
export function bs(value: string | null | undefined): string {
  return `${value ?? '0.00'} Bs`;
}

/** "2026-09-30T10:15:00" -> "30/09/2026 10:15" (hora local, sin conversion). */
export function fechaHora(iso: string | null | undefined): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?/.exec(iso ?? '');
  if (!m) {
    return iso ?? '';
  }
  return m[4] ? `${m[3]}/${m[2]}/${m[1]} ${m[4]}:${m[5]}` : `${m[3]}/${m[2]}/${m[1]}`;
}

export function porcentaje(value: string | null | undefined): string {
  return value === null || value === undefined ? '—' : `${value} %`;
}
