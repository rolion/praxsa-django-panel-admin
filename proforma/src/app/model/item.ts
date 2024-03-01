import { iCarPart } from "../interface/iCarPart";

export class CarPartItem implements iCarPart {
  id: number;
  part_name: string;
  length: number;
  quantity: number;
  part_id: number;
  width: number;
  model_id: number;
  installation_price: number;
  constructor(){
      this.id= 0;
      this.part_name= '';
      this.width= 0;
      this.quantity= 0;
      this.part_id= 0;
      this.installation_price= 0;
      this.model_id = 0;
      this.length = 0;
  }
  }
