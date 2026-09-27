import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AppInventario } from '../almacen.model';
import { InventarioViewComponent } from './inventario-view.component';

const sampleInventario: AppInventario = {
  id: 7, sucursal: 1, sucursal_name: 'Central', bobina: 1, window_film_name: 'Carbon 20%',
  bobina_width: '1.50', quantity: 3, to_install: '50.00', installed: '0.00',
  original_length: '50.00', date: '2026-09-27T00:00:00Z', numero_referencia: 0,
  precio_compra_mtr_lineal: '80.00', precio_venta_mtr_lineal: '120.00', nro_lote: 'L1',
  is_active: true,
};

describe('InventarioViewComponent', () => {
  let httpMock: HttpTestingController;
  const base = `${environment.apiUrl}/product/almacen/inventario`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [InventarioViewComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: '7' }) } } },
      ],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('carga el detalle del inventario', () => {
    const fixture = TestBed.createComponent(InventarioViewComponent);
    fixture.detectChanges();
    httpMock.expectOne(`${base}/7/`).flush(sampleInventario);

    const component = fixture.componentInstance;
    expect(component.inventario).toEqual(sampleInventario);
    expect(component.loading).toBe(false);
  });

  it('muestra un error si falla la carga', () => {
    const fixture = TestBed.createComponent(InventarioViewComponent);
    fixture.detectChanges();
    httpMock.expectOne(`${base}/7/`).flush({}, { status: 404, statusText: 'Not Found' });

    expect(fixture.componentInstance.errorMessage).toBe('No se pudo cargar el inventario.');
  });
});
