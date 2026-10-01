import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { ReelCatalogItem } from '../ordenes/ordenes.model';
import { AppCarModelPart } from '../vehicles/vehicles.model';
import {
  PublicCalculatorInfo,
  PublicInventoryResponse,
  PublicModelPartsResponse,
  mapCatalog,
  mapInventory,
  mapModelParts,
} from './calculadora.helpers';
import { CalcCatalog } from './calculadora.model';

/** Catalogo PUBLICO de la calculadora: no exige sesion y lo puede usar cualquier persona
 * (ADR-pricing-calculator-screen-catalogo-publico-calculadora). Las respuestas se adaptan
 * a los tipos de la pantalla; los importes son vista previa (el servidor recalcula al guardar).
 *
 *  - GET product/calculator_info             -> sucursales, marcas y modelos (activos, con imagen)
 *  - GET product/model_parts/<modelo>        -> items (cristales) del modelo
 *  - GET product/get_inventory/<sucursal>/0/0 -> bobinas con stock y precio por metro
 *                                               (con throttle de 60/min por IP, ADR-005) */
@Injectable({ providedIn: 'root' })
export class CalculadoraService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/product`;

  catalog(): Observable<CalcCatalog> {
    return this.http.get<PublicCalculatorInfo>(`${this.base}/calculator_info`).pipe(map(mapCatalog));
  }

  items(modelId: number): Observable<AppCarModelPart[]> {
    return this.http.get<PublicModelPartsResponse>(`${this.base}/model_parts/${modelId}`).pipe(map(mapModelParts));
  }

  reels(sucursalId: number): Observable<ReelCatalogItem[]> {
    return this.http.get<PublicInventoryResponse>(`${this.base}/get_inventory/${sucursalId}/0/0`).pipe(map(mapInventory));
  }
}
