import { Injectable, inject } from '@angular/core';
import { HttpRequest, HttpHandler, HttpEvent, HttpInterceptor } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from '../service/auth.service';

@Injectable()
export class JwtInterceptor implements HttpInterceptor {
  private authenticationService = inject(AuthService);

  intercept(
    request: HttpRequest<unknown>,
    next: HttpHandler
  ): Observable<HttpEvent<unknown>> {
    // add authorization header with the DRF Token auth scheme if available
    // (praxsa_manager usa rest_framework.authtoken, no JWT -- ver ADR
    // modulo-usuarios-perfiles-grupos-roles-sucursales-api-autenticacion-admin)
    const currentUser = this.authenticationService.currentUserValue;
    if (currentUser && currentUser.token) {
      request = request.clone({
        setHeaders: {
          Authorization: `Token ${currentUser.token}`,
        },
      });
    }

    return next.handle(request);
  }
}
