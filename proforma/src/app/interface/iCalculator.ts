import { CarPartItem } from "../model/item";
import { Film, Car_Part_Film_Price } from "../model/lamina";
import { Marca } from "../model/marca";
import { Modelo } from "../model/modelo";

export interface icalculatorInfo{
  modelos: Modelo[];
  marca: Marca[];
  lamina: Film[] ;
  model_parts: CarPartItem[];
  lamina_price: Car_Part_Film_Price[];
}