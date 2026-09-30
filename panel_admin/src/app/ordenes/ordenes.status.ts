/** Clase CSS del badge de estado (assets/scss/_ordenes.scss) para cualquiera de los
 * estados del flujo de la orden: global de la proforma, nota de trabajo y nota de venta. */
export function statusClass(status: string | null | undefined): string {
  switch (status) {
    case 'proforma':
      return 'status-proforma';
    case 'en_trabajo':
    case 'en_proceso':
      return 'status-progress';
    case 'por_cobrar':
      return 'status-cobrar';
    case 'terminado':
      return 'status-done';
    case 'finalizado':
    case 'pagada':
      return 'status-final';
    case 'anulada':
    case 'cancelada':
      return 'status-void';
    default:
      return 'status-proforma';
  }
}

/** Opciones del filtro por estado global de la orden (listado de proformas). */
export const ORDER_STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'Todos los estados' },
  { value: 'proforma', label: 'Proforma' },
  { value: 'en_trabajo', label: 'En trabajo' },
  { value: 'por_cobrar', label: 'Por cobrar' },
  { value: 'finalizado', label: 'Finalizado' },
  { value: 'anulada', label: 'Anulada' },
];
