export interface AppCarBrand {
  id: number;
  name: string;
  is_active: boolean;
  models_count: number;
}

export interface AppCarPart {
  id: number;
  name: string;
  is_active: boolean;
}

export interface AppCarModel {
  id: number;
  name: string;
  car_brand_id: number;
  car_brand_name: string;
  image: string | null;
  is_active: boolean;
  items_count: number;
}

export interface AppCarModelPart {
  id: number;
  car_part_id: number;
  car_part_name: string;
  width: string;
  length: string;
  quantity: number;
  installation_price: string;
}

export interface CarModelItemPayload {
  car_part_id?: number;
  new_car_part_name?: string;
  width: string;
  length: string;
  quantity: number;
  installation_price: string;
}
