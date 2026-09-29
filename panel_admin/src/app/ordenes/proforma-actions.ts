import Swal from 'sweetalert2';

/** Confirmacion previa de "Generar nota de trabajo": la accion descuenta
 * inventario y cierra la proforma, asi que no debe dispararse por error. */
export function confirmGenerateNota(proformaId: number): Promise<boolean> {
  return Swal.fire({
    title: `¿Generar la nota de trabajo de la proforma ${proformaId}?`,
    text: 'Se descontarán los metros del inventario y la proforma quedará cerrada (ya no se podrá editar).',
    showCancelButton: true,
    confirmButtonText: 'Generar',
    cancelButtonText: 'Cancelar',
  }).then((result) => result.isConfirmed);
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
