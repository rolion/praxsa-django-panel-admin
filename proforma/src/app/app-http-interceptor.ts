import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpHandler, HttpRequest, HttpEvent }
  from '@angular/common/http';
import { Observable } from 'rxjs';
import { LocalStorageService } from './service/local-storage/local-storage.service';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
    constructor(private local: LocalStorageService){}
    intercept(req : HttpRequest<any>, next : HttpHandler) : Observable<HttpEvent<any>> {
        let token = this.local.getData('token');
        let autReq = req;
        if(token){
            autReq = req.clone({
                headers: req.headers.set('Authorization', `Token ${token}`)
              });
        }
      
      return next.handle(token? autReq: req);
    }
}