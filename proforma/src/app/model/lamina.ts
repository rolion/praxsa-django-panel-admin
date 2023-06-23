export class Car_Part_Film_Price {
    film_name: string;
    width: number;
    reel_id: number;
    price: number;
    url: string;
    film_id: number
    constructor(
        film_name: string,
        film_id: number,
        width: number,
        reel_id: number,
        price: number,
        url: string){
            this.film_name= film_name;
            this.film_id = film_id
            this.width= width;
            this.reel_id= reel_id;
            this.price= price;
            this.url= url;        }

}

export class Film {
    id: number;
    name: string;
    url: string
    constructor(id: number, name: string, url: string = ''){
        this.id = id;
        this.name = name;
        this.url = url
    }
}