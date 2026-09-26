import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  AppCarBrand,
  AppCarModel,
  AppCarModelPart,
  AppCarPart,
  CarModelItemPayload,
  UpdateModelItemPayload,
} from './vehicles.model';

interface ListParams {
  search?: string;
  includeInactive?: boolean;
}

function buildParams(params: ListParams = {}): Record<string, string> {
  const query: Record<string, string> = {};
  if (params.search) {
    query['search'] = params.search;
  }
  if (params.includeInactive) {
    query['include_inactive'] = 'true';
  }
  return query;
}

@Injectable({
  providedIn: 'root',
})
export class VehiclesService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/product/vehicles`;

  // Marcas
  listBrands(params: ListParams = {}): Observable<AppCarBrand[]> {
    return this.http.get<AppCarBrand[]>(`${this.base}/brands`, { params: buildParams(params) });
  }

  getBrand(id: number): Observable<AppCarBrand> {
    return this.http.get<AppCarBrand>(`${this.base}/brands/${id}/`);
  }

  createBrand(name: string): Observable<AppCarBrand> {
    return this.http.post<AppCarBrand>(`${this.base}/brands`, { name });
  }

  updateBrand(id: number, name: string): Observable<AppCarBrand> {
    return this.http.patch<AppCarBrand>(`${this.base}/brands/${id}/`, { name });
  }

  toggleBrandActive(id: number, isActive: boolean): Observable<AppCarBrand> {
    return this.http.patch<AppCarBrand>(`${this.base}/brands/${id}/toggle-active/`, {
      is_active: isActive,
    });
  }

  // Items
  listParts(params: ListParams = {}): Observable<AppCarPart[]> {
    return this.http.get<AppCarPart[]>(`${this.base}/parts`, { params: buildParams(params) });
  }

  getPart(id: number): Observable<AppCarPart> {
    return this.http.get<AppCarPart>(`${this.base}/parts/${id}/`);
  }

  createPart(name: string): Observable<AppCarPart> {
    return this.http.post<AppCarPart>(`${this.base}/parts`, { name });
  }

  updatePart(id: number, name: string): Observable<AppCarPart> {
    return this.http.patch<AppCarPart>(`${this.base}/parts/${id}/`, { name });
  }

  togglePartActive(id: number, isActive: boolean): Observable<AppCarPart> {
    return this.http.patch<AppCarPart>(`${this.base}/parts/${id}/toggle-active/`, {
      is_active: isActive,
    });
  }

  // Modelos
  listModels(params: ListParams & { carBrandId?: number } = {}): Observable<AppCarModel[]> {
    const query = buildParams(params);
    if (params.carBrandId) {
      query['car_brand_id'] = String(params.carBrandId);
    }
    return this.http.get<AppCarModel[]>(`${this.base}/models`, { params: query });
  }

  getModel(id: number): Observable<AppCarModel> {
    return this.http.get<AppCarModel>(`${this.base}/models/${id}/`);
  }

  createModel(name: string, carBrandId: number, image?: File | null): Observable<AppCarModel> {
    const formData = new FormData();
    formData.append('name', name);
    formData.append('car_brand_id', String(carBrandId));
    if (image) {
      formData.append('image', image);
    }
    return this.http.post<AppCarModel>(`${this.base}/models`, formData);
  }

  updateModel(
    id: number,
    name: string,
    carBrandId: number,
    image?: File | null
  ): Observable<AppCarModel> {
    if (image === undefined) {
      return this.http.patch<AppCarModel>(`${this.base}/models/${id}/`, {
        name,
        car_brand_id: carBrandId,
      });
    }
    const formData = new FormData();
    formData.append('name', name);
    formData.append('car_brand_id', String(carBrandId));
    formData.append('image', image === null ? '' : image);
    return this.http.patch<AppCarModel>(`${this.base}/models/${id}/`, formData);
  }

  toggleModelActive(id: number, isActive: boolean): Observable<AppCarModel> {
    return this.http.patch<AppCarModel>(`${this.base}/models/${id}/toggle-active/`, {
      is_active: isActive,
    });
  }

  // Items asociados a un Modelo (Car_Model_Part)
  listModelItems(modelId: number): Observable<AppCarModelPart[]> {
    return this.http.get<AppCarModelPart[]>(`${this.base}/models/${modelId}/items/`);
  }

  addModelItem(modelId: number, payload: CarModelItemPayload): Observable<AppCarModelPart> {
    return this.http.post<AppCarModelPart>(`${this.base}/models/${modelId}/items/`, payload);
  }

  updateModelItem(
    modelId: number,
    itemId: number,
    payload: UpdateModelItemPayload
  ): Observable<AppCarModelPart> {
    return this.http.patch<AppCarModelPart>(`${this.base}/models/${modelId}/items/${itemId}/`, payload);
  }

  removeModelItem(modelId: number, itemId: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/models/${modelId}/items/${itemId}/`);
  }
}
