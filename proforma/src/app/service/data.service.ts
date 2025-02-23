import { Inject, Injectable, PLATFORM_ID } from '@angular/core';
import {Modelo} from '../model/modelo';
import {CarPartItem} from '../model/item';
import {Sucursal} from '../model/sucursal';
import {Film, Car_Part_Film_Price} from '../model/lamina';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';
import {HttpClient, HttpHeaders} from '@angular/common/http';
import {Marca} from '../model/marca';
import { environment } from '../../environments/environment';
import { icalculatorInfo } from '../interface/iCalculator';
import { iInventory } from '../interface/iInventory';
import { iCarPart } from '../interface/iCarPart';
import { isPlatformBrowser } from '@angular/common';

@Injectable({
  providedIn: 'root'
})

export class DataService {

  modeloArray: Modelo[] = [];
  itemArray: CarPartItem[] = [];
  precioArray: Film[] = [];
  marcaArray: Marca[] = [];
  base_url: string;
  headers = new HttpHeaders({'Content-Type': 'text; charset=UTF-8'});
  constructor(private http: HttpClient, @Inject(PLATFORM_ID) plataformId: Object) {
    this.base_url = isPlatformBrowser(plataformId)? environment.BROWSER_APP_BASE_REF: environment.SERVER_APP_BASE_REF; 
  }

  getCalculatorInfo(): Observable<icalculatorInfo>{
    return this.http
      .get<icalculatorInfo>(`${this.base_url}/product/calculator_info`)
      .pipe(
        map((res: any)  => {
          const modelos: Modelo[] = [];
          const marca: Marca[] = [];
          const lamina: Film[] = []
          const model_parts: CarPartItem[] = []
          const lamina_price: Car_Part_Film_Price[] = []
          const sucursal: Sucursal[]= []
          if(res.sucursales && Array.isArray(res.sucursales)){
            res.sucursales.forEach((obj: Sucursal) => {
              sucursal.push(obj)
            })
          }
          if(res.models && Array.isArray(res.models)){
            res.models.forEach((model: any) => {
              modelos.push(new Modelo( model.id, model.brand_id, model.name));
            })
          }
          if(res.brands && Array.isArray(res.brands)){
            res.brands.forEach((brand: any) => {
              marca.push(new Marca( brand.id, brand.name));
            })
          }
          if(res.model_parts && Array.isArray(res.model_parts)){
            res.model_parts.forEach((part: any) => {
              model_parts.push(part);
            })
          }
          let response = {modelos, marca, lamina, model_parts, lamina_price, sucursal}
          
          return response
        })
      )
  }
  getInventario(sucursalId: Number, laminaId: Number = 0, width: number = 0):Observable<iInventory[]>{
    return this.http
    .get<iInventory[]>(`${this.base_url}/product/get_inventory/${sucursalId}/${laminaId}/${width}`)
      .pipe(
        map((res: any)  => {
          let inventario: iInventory[]=[];
          if(res.inventario && Array.isArray(res.inventario)){
            inventario = res.inventario
          }
          return inventario;
    }))
  }
  getModelParts(modelId: Number):Observable<iCarPart[]>{
    return this.http
    .get<iCarPart[]>(`${this.base_url}/product/model_parts/${modelId}`)
    .pipe(
      map((res: any)=>{
        let carParts: iCarPart[]=[]
          if(res.car_parts && Array.isArray(res.car_parts)){
            carParts = res.car_parts
          }
          return carParts;
      }))
  }
}
