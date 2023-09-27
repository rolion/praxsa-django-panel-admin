import { CarPartItem } from "../model/item";
import { Film, Car_Part_Film_Price } from "../model/lamina";
import { Marca } from "../model/marca";
import { Sucursal } from "../model/sucursal";
import { Modelo } from "../model/modelo";
import { iInventory } from "./iInventory";

export interface icalculatorInfo{
  modelos: Modelo[];
  marca: Marca[];
  lamina: Film[] ;
  model_parts: CarPartItem[];
  lamina_price: iInventory[];
  sucursal: Sucursal[];
}