import {ReportItem} from './report';

export class ProformaCollection{
  items: any[];
  // carPartItmes:CarPartFilmItem[]| null | undefined;; 
  car_model_name: string;
  car_model_id: number;
  name: string | null | undefined;
  email: string | null | undefined;
  phone_number: string | null | undefined;
  ci_nit: string | null | undefined;
  placa: string | null | undefined;
  total_price: number;
  car_brand_name: string;
  car_plate: string| null | undefined;

  constructor(items: ReportItem[], 
    car_brand_name: string, 
    car_model_name: string,
    car_model_id: number,
    total: number){
    this.items = items.map(val => {
      return {
        item: val.item.part_name, 
        lamina: val.lamina?.name, 
        cantidad: val.cantidad, 
        subtotal: val.subtotal};
    });
    this.car_brand_name = car_brand_name;
    this.car_model_name = car_model_name;
    this.car_model_id = car_model_id
    this.total_price = total;
  }
}



export class CarPartFilmItem {
  car_part: number;
  car_part_name: string;
  width : number;
  length: number;
  sub_total: number;
  quantity: number;
  window_film: number;
  window_film_name: string;
  installation_price: number;
  window_film_price: number;
  window_film_url: string;
  constructor(
    car_part_id: number,
    car_part_name: string,
    width : number,
    length: number,
    sub_total: number,
    quantity: number,
    window_film_id: number,
    //window_film_name: string,
    installation_price: number,
    window_film_price: number,
  ){
    this.car_part = car_part_id;
    this.car_part_name = car_part_name;
    this.width  = width;
    this.length = length;
    this.sub_total = sub_total;
    this.quantity = quantity;
    this.window_film = window_film_id;
    this.window_film_url = '';
    this.installation_price= installation_price;
    this.window_film_price= window_film_price;
    this.window_film_name = '';
  }
}

export class Invoice{
  id: number;
  carPartItems: CarPartFilmItem[];
  name: string;
  ci_nit: string;
  car_plate: string;
  sucursal: number;
  sucursal_name: string;
  sucursal_address: string;
  sucursal_phone: string;
  car_model_id: number;
  car_model_name: string;
  car_brand_id: number;
  car_brand_name: string;
  email: string | null | undefined;
  phone_number: string | null | undefined;
  ci: string | null | undefined;
  placa: string | null | undefined;
  total_price: number;
  proforma_created_on: string;
  status: string;

  constructor(
    carPartItems: CarPartFilmItem[],
    car_model_id: number, 
    car_model_name: string,
    car_brand_id: number, 
    car_brand_name: string,
    total_price: number,
    sucursal_addres: string = '',
    sucursal_phone: string = ''){
    this.id = 0;
    this.carPartItems = carPartItems;
    this.name = "";
    this.email = "",
    this.ci_nit = "",
    this.car_plate = "",
    this.car_model_id = car_model_id;
    this.car_model_name = car_model_name;
    this.car_brand_id = car_brand_id, 
    this.car_brand_name = car_brand_name,
    this.total_price = total_price;
    this.phone_number = '';
    this.proforma_created_on = '';
    this.status = '';
    this.sucursal = 0;
    this.sucursal_name = ''
    this.sucursal_address = sucursal_addres,
    this.sucursal_phone = sucursal_phone
  }
}
