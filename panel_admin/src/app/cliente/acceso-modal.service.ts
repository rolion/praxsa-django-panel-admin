import { Injectable, inject } from '@angular/core';
import { NgbModal, NgbModalRef } from '@ng-bootstrap/ng-bootstrap';
import { AccesoModalComponent } from './acceso-modal.component';
import { AccesoMode } from './cliente.model';

/** Abre el modal de acceso (iniciar sesion / crear cuenta). Lo usan el encabezado y la
 * calculadora. Resuelve `true` si la persona quedo con sesion iniciada y `false` si cerro
 * el modal sin autenticarse. Nunca hay dos modales de acceso a la vez. */
@Injectable({ providedIn: 'root' })
export class AccesoModalService {
  private modalService = inject(NgbModal);
  private current: NgbModalRef | null = null;

  open(mode: AccesoMode = 'login', message = ''): Promise<boolean> {
    if (this.current) {
      return this.current.result.then(
        (ok) => ok === true,
        () => false
      );
    }
    const ref = this.modalService.open(AccesoModalComponent, {
      ariaLabelledBy: 'acceso-modal-title',
      // No se cierra por clic fuera ni con Escape mientras envia datos.
      beforeDismiss: () => !ref.componentInstance.busy(),
      centered: true,
    });
    this.current = ref;
    ref.componentInstance.message = message;
    ref.componentInstance.setMode(mode);
    return ref.result.then(
      (ok) => {
        this.current = null;
        return ok === true;
      },
      () => {
        this.current = null;
        return false;
      }
    );
  }
}
