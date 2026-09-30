import { AppNotaVenta } from '../ordenes.model';

/** Motivo por el que "Registrar pago" no se puede usar todavia (vacio = se puede).
 * Es una precondicion de negocio (no un permiso): el boton se deshabilita con
 * tooltip; el servidor la vuelve a validar (ADR-...-maquina-de-estados). */
export function payBlockReason(nv: Pick<AppNotaVenta, 'work_status'>): string {
  return nv.work_status === 'terminado' ? '' : 'El trabajo aún no está terminado.';
}

/** Motivo por el que "Anular nota de venta" no se puede usar todavia (vacio = se puede). */
export function anularBlockReason(nv: Pick<AppNotaVenta, 'work_status'>): string {
  return nv.work_status === 'terminado'
    ? 'El trabajo ya está terminado; corrija el trabajo antes de anular.'
    : '';
}
