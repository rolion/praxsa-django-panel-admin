import { Injectable, Inject, PLATFORM_ID, } from '@angular/core';
import {HttpClient, HttpHeaders} from '@angular/common/http';
import { User } from 'src/app/model/user';  
import { BehaviorSubject, Observable } from 'rxjs';
import {map, retry} from 'rxjs/operators';
import { environment } from '../../../../environments/environment';
import { Credentials } from 'src/app/model/credentials';
import { LocalStorageService } from '../../local-storage/local-storage.service';
import { isPlatformBrowser } from '@angular/common';

@Injectable({
  providedIn: 'root'
})
export class AutheticationService {

  httpOptions = {
    headers: new HttpHeaders({
      'Content-Type':  'application/json',
    })
  };
  base_url: String;
  private userLoginSource: BehaviorSubject<User|null>;
  isUserLoged: Observable<User|null>;
  plataformId: Object;


  constructor(private http: HttpClient, private local: LocalStorageService, @Inject(PLATFORM_ID) plataformId: Object) {
    this.base_url = isPlatformBrowser(plataformId)? environment.BROWSER_APP_BASE_REF: environment.SERVER_APP_BASE_REF;
    this.userLoginSource = new BehaviorSubject(this.restoreMinimalSession())
    this.isUserLoged = this.userLoginSource.asObservable()
    this.plataformId = plataformId;

   }

  createUser(newUser: User): Observable<{data: User}>{
    return this.http 
      .post<User>(`${this.base_url}/product/create_client`, newUser, this.httpOptions)
      .pipe(
        map((res: any)  => {
          return {data: res};
        })
      )
  }
  login(crendentials: Credentials): Observable<User>{
    return this.http.post<Credentials>(`${this.base_url}/product/api-token-auth/`, crendentials, this.httpOptions)
    .pipe(map((res: any) => {
        // Solo token+name se persisten en localStorage (TASK-004/ADR-003); el
        // resto del perfil vive únicamente en memoria (userLoginSource) durante
        // la sesión del SPA, se pierde en un refresh de página.
        this.local.saveData('token', res.token)
        this.local.saveData('name', res.name)
        let user = new User(res.email,'', res.name, res.lastname, res.phone_number, res.ci_nit)
        this.userLoginSource.next(user)
        return user
      })
    )
  }
  logout(){
    if (this.local.getData('token')){
        this.local.removeData('token')
        this.local.removeData('name')
        // Limpia también las claves que este servicio ya no escribe desde
        // login(), por si quedaron de una sesión anterior a este cambio.
        this.local.removeData('lastname')
        this.local.removeData('phone_number')
        this.local.removeData('email')
        this.local.removeData('ci_nit')
        this.userLoginSource.next(null)
    }
  }
  getUser(): User | null{
    return this.userLoginSource.value;
  }
  /** Reconstruye el estado mínimo de sesión (token+name) desde localStorage al
   * arrancar la app. lastname/email/phone_number/ci_nit quedan vacíos hasta el
   * próximo login() en esta sesión de navegador — no se persisten (TASK-004). */
  private restoreMinimalSession(): User | null {
    if (this.local.getData('token')) {
      return new User('', '', `${this.local.getData('name')}`, '', '', '');
    }
    return null;
  }
}
