import Swal from 'sweetalert2';

/** Confirmacion previa de una accion que cambia el estado de la orden. */
export function confirmAction(title: string, text: string, confirmButtonText: string): Promise<boolean> {
  return Swal.fire({
    title,
    text,
    showCancelButton: true,
    confirmButtonText,
    cancelButtonText: 'Cancelar',
  }).then((result) => result.isConfirmed);
}

/** "Aprobar y generar orden": descuenta inventario y crea la nota de trabajo y la nota de venta. */
export function confirmGenerateNota(proformaId: number): Promise<boolean> {
  return confirmAction(
    `¿Aprobar la proforma ${proformaId} y generar la orden?`,
    'Se descontarán los metros del inventario, se creará la nota de trabajo y la nota de venta (por cobrar) y la proforma dejará de ser editable.',
    'Aprobar'
  );
}

export function confirmAnularProforma(proformaId: number): Promise<boolean> {
  return confirmAction(
    `¿Anular la proforma ${proformaId}?`,
    'La proforma quedará anulada y ya no se podrá editar ni aprobar.',
    'Anular'
  );
}

export function confirmTerminarTrabajo(proformaId: number): Promise<boolean> {
  return confirmAction(
    `¿Marcar como terminado el trabajo de la proforma ${proformaId}?`,
    'Se registrará la salida del vehículo y la nota de venta podrá cobrarse. La nota de trabajo dejará de ser editable.',
    'Marcar terminado'
  );
}

export function confirmCorregirTrabajo(proformaId: number): Promise<boolean> {
  return confirmAction(
    `¿Volver a poner En proceso el trabajo de la proforma ${proformaId}?`,
    'La nota de trabajo volverá a poder editarse.',
    'Corregir trabajo'
  );
}

/** Anular la nota de trabajo o la de venta ejecutan la misma operacion (reabrir la proforma). */
export function confirmAnularOrden(proformaId: number | null, what: 'nota de trabajo' | 'nota de venta'): Promise<boolean> {
  return confirmAction(
    `¿Anular la ${what}${proformaId ? ' de la proforma ' + proformaId : ''}?`,
    'Se cancelarán la nota de trabajo y la nota de venta, se devolverá el inventario y la proforma volverá a estar vigente para editarla o volver a aprobarla.',
    'Anular'
  );
}

export function confirmAnularPago(notaVentaId: number): Promise<boolean> {
  return confirmAction(
    `¿Anular el pago de la nota de venta ${notaVentaId}?`,
    'La nota de venta volverá a estar por cobrar.',
    'Anular pago'
  );
}

export function showErrorAlert(title: string, text: string): void {
  Swal.fire({ title, text, icon: 'error' });
}

/** Dispara la descarga de un archivo ya recibido como Blob. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
