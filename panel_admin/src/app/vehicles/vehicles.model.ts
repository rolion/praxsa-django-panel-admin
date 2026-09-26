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
  /** Oculto en el formulario del panel a pedido del usuario (2026-09-26).
   * Si se omite, el backend usa el default del modelo (0). */
  installation_price?: string;
}

/** Editar una asociación ya creada solo permite tocar estos 3 campos -- el
 * item asociado (car_part_id) no se puede cambiar desde aquí. */
export interface UpdateModelItemPayload {
  width: string;
  length: string;
  quantity: number;
}
