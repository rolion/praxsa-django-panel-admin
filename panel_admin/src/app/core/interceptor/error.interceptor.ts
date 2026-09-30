import { AuthService } from '../service/auth.service';
import { Injectable, inject } from '@angular/core';
import { HttpRequest, HttpHandler, HttpEvent, HttpInterceptor, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

@Injectable()
export class ErrorInterceptor implements HttpInterceptor {
  private authenticationService = inject(AuthService);

  intercept(
    request: HttpRequest<unknown>,
    next: HttpHandler
  ): Observable<HttpEvent<unknown>> {
    return next.handle(request).pipe(
      catchError((err: HttpErrorResponse) => {
        if (err.status === 401) {
          // Se decide segun la sesion ANTES de cerrarla.
          const wasClient = this.authenticationService.isClient;
          // auto logout if 401 response returned from api
          this.authenticationService.logout();
          if (wasClient) {
            // Cliente: sin recarga (se perderia la cotizacion); la pantalla reabre el
            // modal de acceso (ADR-pricing-calculator-screen-sesion-cliente-aislamiento).
            this.authenticationService.notifySessionExpired();
          } else if (this.shouldReload(request)) {
            this.reload();
          }
        }

        // Se propaga el HttpErrorResponse original (no un string derivado) para
        // que cada consumidor decida cómo interpretar status/body del error
        // (ej. distinguir sin conexión de credenciales inválidas en el login).
        return throwError(() => err);
      })
    );
  }

  /** Staff: comportamiento de siempre (recarga). Una llamada anonima a rutas publicas
   * (sin token) que recibe 401 no debe recargar la calculadora. */
  private shouldReload(request: HttpRequest<unknown>): boolean {
    return request.headers.has('Authorization');
  }

  protected reload(): void {
    location.reload();
  }
}
