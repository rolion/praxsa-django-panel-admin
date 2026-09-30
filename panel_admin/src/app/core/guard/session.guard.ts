import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';

import { AuthService } from '../service/auth.service';

/** Guard de las rutas de cliente que exigen sesion (`/mis-proformas`). Sin sesion
 * vuelve a la calculadora con el modal de acceso abierto (`?acceso=1`); el staff no
 * tiene lista de cliente y va al panel. */
@Injectable({
  providedIn: 'root',
})
export class SessionGuard {
  private authService = inject(AuthService);
  private router = inject(Router);

  canActivate() {
    if (this.authService.isClient) {
      return true;
    }
    if (this.authService.isStaff) {
      this.router.navigate(['/dashboard/main']);
    } else {
      this.router.navigate(['/calculadora'], { queryParams: { acceso: 1 } });
    }
    return false;
  }
}
