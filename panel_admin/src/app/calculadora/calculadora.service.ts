import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { OrdenesService } from '../ordenes/ordenes.service';
import { OrdenSucursal, ReelCatalogItem } from '../ordenes/ordenes.model';
import { VehiclesService } from '../vehicles/vehicles.service';
import { AppCarBrand, AppCarModel, AppCarModelPart } from '../vehicles/vehicles.model';

/** Fachada fina sobre los servicios existentes (sin endpoints nuevos). Todas las
 * llamadas son API staff con alcance por sucursal:
 *  - sucursales / bobinas -> `product/ordenes/catalogo/*`
 *  - marcas / modelos / items -> `product/vehicles/*`
 * (ADR-pricing-calculator-screen-cotizacion-en-cliente). */
@Injectable({ providedIn: 'root' })
export class CalculadoraService {
  private ordenes = inject(OrdenesService);
  private vehicles = inject(VehiclesService);

  sucursales(): Observable<OrdenSucursal[]> {
    return this.ordenes.listSucursales();
  }

  brands(): Observable<AppCarBrand[]> {
    return this.vehicles.listBrands();
  }

  modelsByBrand(carBrandId: number): Observable<AppCarModel[]> {
    return this.vehicles.listModels({ carBrandId });
  }

  items(modelId: number): Observable<AppCarModelPart[]> {
    return this.vehicles.listModelItems(modelId);
  }

  reels(sucursalId: number): Observable<ReelCatalogItem[]> {
    return this.ordenes.listBobinas(sucursalId);
  }
}
