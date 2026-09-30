/** Convierte el cuerpo de error de DRF (`{detail}`, `{campo: [msg]}`,
 * `{items: [msg, ...]}` o una lista) en un unico texto legible para mostrar. */
export function extractApiError(err: unknown, fallback: string): string {
  const body = (err as { error?: unknown } | null)?.error;
  const messages = collect(body);
  return messages.length ? messages.join(' ') : fallback;
}

function collect(value: unknown): string[] {
  if (value === null || value === undefined) {
    return [];
  }
  if (typeof value === 'string') {
    return [value];
  }
  if (Array.isArray(value)) {
    return value.flatMap(collect);
  }
  if (typeof value === 'object') {
    return Object.values(value as Record<string, unknown>).flatMap(collect);
  }
  return [];
}
