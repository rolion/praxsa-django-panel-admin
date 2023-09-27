import { CarPartItem } from "src/app/model/item";
import { Film, Car_Part_Film_Price } from "src/app/model/lamina";
import { Marca } from "src/app/model/marca";
import { Modelo } from "src/app/model/modelo";
import { Sucursal } from "src/app/model/sucursal";

export class iDB
{
    marcas: Marca[] =[];
    model: Modelo[] = [];
    films: Film[] = [];
    prices: Car_Part_Film_Price[] = [];
    carParts: CarPartItem[] = [];
    sucursales: Sucursal[] = []
    constructor(){
    }

    getModelByMarca(marcaId: number): Modelo[] {
        return this.model.filter(item => item.idMarca == marcaId);
    }

    getModelParts(modelId: number): CarPartItem[]{
        return this.carParts.filter(item => item.model_id == modelId);
    }

    getLamninaPrices(laminaId: number){
        return this.prices.filter(price => price.bobina_film_id === laminaId)
    }

    getLamninaPriceByWidth(laminaId: number, width: number): Car_Part_Film_Price{
        let laminaPrices = this.getLamninaPrices(laminaId);
        let prices = laminaPrices.filter(film => film.bobina_width === width);
        if (prices.length == 0){
            let wider_films = laminaPrices.filter(price => price.bobina_width > width);
            let price = wider_films.reduce((acc, curr) =>{
                if(acc != null && acc!=undefined){
                    let discriminate_acc = acc.bobina_width - width;
                    let discriminate_curr = curr.bobina_width - width;
                    if(discriminate_acc >discriminate_curr){
                        return curr;
                    }else{
                        return acc;
                    }
                }else{
                    return curr;
                }
            } )
            prices =[price];
        } 

        return prices[0];
    }
}