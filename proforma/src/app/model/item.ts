export class CarPartItem{
  id: number;
  part_name: string;
  width: number;
  quantity: number;
  part_id: number;
  installation_price: number;
  model_id: number
  constructor(id: number, 
    part_name: string, 
    width: number, 
    quantity: number, 
    part_id: number,
    installation_price: number, 
    model_id: number){
      this.id= id;
      this.part_name= part_name;
      this.width= width;
      this.quantity= quantity;
      this.part_id= part_id;
      this.installation_price= installation_price;
      this.model_id = model_id
  }
  }
