import {Modelo} from './modelo';
import {CarPartItem} from './item';
import {Car_Part_Film_Price, Film} from './lamina';
import { CarPartFilmItem } from './proformaCollection';

export class ReportItem{
  modelo: Modelo;
  item: CarPartItem;
  cantidad: number ;
  precio: number = 0;
  subtotal: number = 0;
  precioMtl: number = 0;
  lamina: Film | null;
  lamina_prices: Car_Part_Film_Price[] | null;
  constructor(modelo: Modelo, 
    item: CarPartItem, 
    cantidad: number, 
    lamina: Film | null, 
    lamina_prices: Car_Part_Film_Price[]| null) {
    this.modelo = modelo;
    this.item = item;
    this.lamina = lamina;
    this.cantidad  = cantidad;
    this.lamina_prices = lamina_prices;
    if ( lamina != null ){
      this.calculateSubtotal();
    }else{
      this.subtotal = 0 ;
      this.lamina = null;
    }

  }
  addLamina( lamina: Film | null ): void{
      this.lamina = lamina;
      this.calculateSubtotal();
  }
  addCantidad( cantidad: number ): void{
    this.cantidad = cantidad;
    this.calculateSubtotal();
  }
  calculateSubtotal(): void{
    if(this.lamina){
      this.cantidad = this.item.quantity;
      this.precio = this.lamina_prices?.find(price =>(price.width === this.item.width && price.film_id === this.lamina?.id))?.price || 0
      this.subtotal = this.precio === 0? 0 :(this.item.installation_price + this.precio) * this.item.quantity
    }else{
      this.subtotal = 0;
      this.cantidad = 0;
    }
  }

  // toBeObject():CarPartFilmItem | null {
  //   if(this.lamina){
  //     let length = 0; // todo add lenght to carPartItem
  //     let {
  //       id: car_part_id,
  //       part_name: car_part_name,
  //       width,
  //       quantity,
  //       installation_price
  //     } = this.item
  //     let {
  //       id: window_film_id,
  //       name: window_film_name,
  //     } = this.lamina
  //     let carPartFilmItem: CarPartFilmItem = new CarPartFilmItem(
  //       car_part_id,
  //       car_part_name,
  //       width,
  //       length,
  //       this.subtotal,
  //       quantity,
  //       window_film_id, 
  //       window_film_name,
  //       installation_price,
  //       this.precio);
  //     return carPartFilmItem
  //   }
  //   return null;
  // }
}
