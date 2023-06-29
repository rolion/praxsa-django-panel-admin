import { isPlatformBrowser } from '@angular/common';
import { Inject, Injectable, PLATFORM_ID } from '@angular/core';
import { ignoreElements } from 'rxjs';



@Injectable({
  providedIn: 'root'
})
export class LocalStorageService {

  plataformId: Object;

  constructor(@Inject(PLATFORM_ID) plataformId: Object) {
    this.plataformId = plataformId;
   }

  public saveData(key: string, value: string) {
    if(isPlatformBrowser(this.plataformId)){
      localStorage.setItem(key, value);
    }
  }

  public getData(key: string) {
    if(isPlatformBrowser(this.plataformId)){
      return localStorage.getItem(key)
    }else{
      return null;
    }
    
  }
  public removeData(key: string) {
    if(isPlatformBrowser(this.plataformId)){
      localStorage.removeItem(key);
    }
    
  }

  public clearData() {
    if(isPlatformBrowser(this.plataformId)){
      localStorage.clear();
    }
  }
}
