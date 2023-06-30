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
    this.userLoginSource = new BehaviorSubject(this.getUser())
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
        this.local.saveData('token', res.token)
        this.local.saveData('name', res.name)
        this.local.saveData('lastname', res.lastname)
        this.local.saveData('phone_number', res.phone_number)
        this.local.saveData('email', res.email)
        this.local.saveData('ci_nit', res.ci_nit)
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
        this.local.removeData('lastname')
        this.local.removeData('phone_number')
        this.local.removeData('ci_nit')
        this.userLoginSource.next(null)
    }
  }
  getUser(): User | null{
    let user : User | null = null;
    if (this.local.getData('token')){
      user = new User(
        `${this.local.getData('email')}`,
        '', 
        `${this.local.getData('name')}`, 
        `${this.local.getData('lastname')}`, 
        `${this.local.getData('phone_number')}`, 
        `${this.local.getData('ci_nit')}`)
    }
    return user;
  }
}
