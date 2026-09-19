import { Injectable, Injector } from '@angular/core';
import { HttpInterceptor, HttpHandler, HttpRequest, HttpEvent, HttpErrorResponse }
  from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { Router } from '@angular/router';
import { LocalStorageService } from './service/local-storage/local-storage.service';
import { AutheticationService } from './service/pybackend/authentication/authetication.service';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
    // AutheticationService se resuelve de forma perezosa via Injector (no en el
    // constructor) porque AutheticationService inyecta HttpClient, y HttpClient
    // depende de este interceptor: inyectarlo directamente crea una dependencia
    // circular en Angular DI.
    constructor(private local: LocalStorageService, private injector: Injector, private router: Router){}
    intercept(req : HttpRequest<any>, next : HttpHandler) : Observable<HttpEvent<any>> {
        let token = this.local.getData('token');
        let autReq = req;
        if(token){
            autReq = req.clone({
                headers: req.headers.set('Authorization', `Token ${token}`)
              });
        }

      return next.handle(token? autReq: req).pipe(
        catchError((error: HttpErrorResponse) => {
          if (error.status === 401) {
            this.injector.get(AutheticationService).logout();
            this.router.navigateByUrl('/login');
          }
          return throwError(() => error);
        })
      );
    }
}