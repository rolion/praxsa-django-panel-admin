import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';

import { AuthService } from '../service/auth.service';

/** Guard del layout de administracion: solo sesiones de staff. Sin sesion va al login
 * del panel; un cliente vuelve a la calculadora. Es una capa de navegacion/UX: la
 * barrera real son los permisos de cada endpoint (`IsStaffUser`,
 * ADR-pricing-calculator-screen-sesion-cliente-aislamiento). */
@Injectable({
  providedIn: 'root',
})
export class StaffGuard {
  private authService = inject(AuthService);
  private router = inject(Router);

  canActivate() {
    if (this.authService.isStaff) {
      return true;
    }
    if (this.authService.isClient) {
      this.router.navigate(['/calculadora']);
    } else {
      this.router.navigate(['/authentication/signin']);
    }
    return false;
  }
}
