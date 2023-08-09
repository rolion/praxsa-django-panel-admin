import { HttpHeaders, HttpClient } from '@angular/common/http';
import { Inject, Injectable, PLATFORM_ID } from '@angular/core';
import { WindowsFilm } from 'src/app/model/windowsFilm';
import { environment } from '../../../../environments/environment';
import {map} from 'rxjs/operators';
import { isPlatformBrowser } from '@angular/common';

@Injectable({
  providedIn: 'root'
})
export class WindowsFilmService {

  httpOptions = {
    headers: new HttpHeaders({
      'Content-Type':  'application/json',
    })
  };

  base_url: Object;

  constructor(private http: HttpClient, @Inject(PLATFORM_ID) plataformId: Object) {
    this.base_url = isPlatformBrowser(plataformId)? environment.BROWSER_APP_BASE_REF: environment.SERVER_APP_BASE_REF;
    console.log('url --->', this.base_url)
    console.log('isPlatformBrowser',isPlatformBrowser(plataformId))
  }

  getWindowsFilmInfo(windows_film_id: number){
    console.log('calling end point')
    console.log('base url ', this.base_url)
    return this.http
    .get<WindowsFilm>(`${this.base_url}/product/layer/${windows_film_id}`,this.httpOptions)
    .pipe(
      map(  (res:any)=>{
        return res;
    })
    )
  }
}
