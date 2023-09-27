import { iInventory } from 'src/app/interface/iInventory';
export class Car_Part_Film_Price implements iInventory {
    bobina_film_name: String;
    bobina_film_id: number;
    bobina_width: number;
    bobina_metros_disponibles: number;
    bobina_price: number;
    bobina_id: number;
    constructor(){
        this.bobina_film_name = '';
        this.bobina_film_id = 0;
        this.bobina_width = 0;
        this.bobina_metros_disponibles = 0;
        this.bobina_price = 0;
        this.bobina_id = 0;
    }
    // film_name: string;
    // width: number;
    // reel_id: number;
    // price: number;
    // url: string;
    // film_id: number
    // constructor(
    //     film_name: string,
    //     film_id: number,
    //     width: number,
    //     reel_id: number,
    //     price: number,
    //     url: string){
    //         this.film_name= film_name;
    //         this.film_id = film_id
    //         this.width= width;
    //         this.reel_id= reel_id;
    //         this.price= price;
    //         this.url= url;        }

}

export class Film {
    id: number;
    name: String;
    url: string
    constructor(){
        this.id = 0;
        this.name = '';
        this.url = ''
    }
}