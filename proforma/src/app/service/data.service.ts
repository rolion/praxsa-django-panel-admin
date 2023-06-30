import { Injectable } from '@angular/core';
import {Modelo} from '../model/modelo';
import {CarPartItem} from '../model/item';
import {Film, Car_Part_Film_Price} from '../model/lamina';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';
import {HttpClient, HttpHeaders} from '@angular/common/http';
import {Marca} from '../model/marca';
import { environment } from '../../environments/environment';
import { icalculatorInfo } from '../interface/iCalculator';

@Injectable({
  providedIn: 'root'
})

export class DataService {

  modeloArray: Modelo[] = [];
  itemArray: CarPartItem[] = [];
  precioArray: Film[] = [];
  marcaArray: Marca[] = [];
  headers = new HttpHeaders({'Content-Type': 'text; charset=UTF-8'});
  constructor(private http: HttpClient) { }

  getCalculatorInfo(): Observable<icalculatorInfo>{
    console.log('app base dir ', environment.SERVER_APP_BASE_REF)
    return this.http
      .get<icalculatorInfo>(`${environment.SERVER_APP_BASE_REF}/product/get_call_info`)
      .pipe(
        map((res: any)  => {
          const modelos: Modelo[] = [];
          const marca: Marca[] = [];
          const lamina: Film[] = []
          const model_parts: CarPartItem[] = []
          const lamina_price: Car_Part_Film_Price[] = []
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
          if(res.films && Array.isArray(res.films)){
            res.films.forEach((film: any) => {
              lamina.push(new Film( film.id, film.name,));
            })
          }
          if(res.car_part_film_price && Array.isArray(res.car_part_film_price)){
            res.car_part_film_price .forEach((film: any) => {
              lamina_price.push(new Car_Part_Film_Price(film.name, film.film_id, film.width, film.reel_id, film.price, ''));
            })
          }
          if(res.model_parts && Array.isArray(res.model_parts)){
            res.model_parts.forEach((part: any) => {
              model_parts.push(new CarPartItem(part.id, part.part_name, part.width, part.quantity, part.part_id, part.installation_price, part.model_id));
            })
          }
          let response = {modelos, marca, lamina, model_parts, lamina_price}
          
          return response
        })
      )
  }
  getModelo(): Observable<Modelo[]>{
    return  this.http
      .get('assets/data/modelo.csv', {responseType: 'text'})
      .pipe(
        map((res: any) => {
          const csvToRowArray = res.split('\n');
          const modelo: Modelo[] = [];
          for (let index = 1; index < csvToRowArray.length - 1; index++) {
            let row = csvToRowArray[index].split(',');
            // console.log('row ', row)
            modelo.push(new Modelo( parseInt( row[0], 10), parseInt( row[1], 10), row[2]));
          }
          return modelo;
        })
      );
  }
  getMarca(): Observable<Marca[]>{
    return  this.http
      .get('assets/data/marca.csv', {responseType: 'text'})
      .pipe(
        map((res: any) => {
          const csvToRowArray = res.split('\n');
          const modelo: Marca[] = [];
          for (let index = 1; index < csvToRowArray.length - 1; index++) {
            let row = csvToRowArray[index].split(',');
            modelo.push(new Marca( parseInt( row[0], 10), row[1]));
          }
          return modelo;
        })
      );
  }
}
