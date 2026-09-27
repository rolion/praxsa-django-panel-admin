import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AppSucursal, AppWindowFilmReel } from '../almacen.model';
import { InventarioCreateComponent } from './inventario-create.component';

const sampleSucursales: AppSucursal[] = [{ id: 1, name: 'Central' }];
const sampleBobinas: AppWindowFilmReel[] = [
  { id: 1, window_film: 1, window_film_name: 'Carbon 20%', width: '1.50', length: '30.00', price: '120.00', is_active: true },
];

describe('InventarioCreateComponent', () => {
  let httpMock: HttpTestingController;
  const base = `${environment.apiUrl}/product/almacen`;

  function createAndLoad() {
    const fixture = TestBed.createComponent(InventarioCreateComponent);
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiUrl}/product/sucursales`).flush(sampleSucursales);
    httpMock.expectOne((r) => r.url === `${base}/bobinas`).flush(sampleBobinas);
    return fixture;
  }

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [InventarioCreateComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('no envia el formulario sin bobina seleccionada (invalido)', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;
    component.form.patchValue({ sucursal: 1, bobina: null });

    component.save();

    httpMock.expectNone(`${base}/inventario`);
    expect(component.form.invalid).toBe(true);
  });

  it('crea el inventario con los campos obligatorios', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;
    component.form.patchValue({
      sucursal: 1, bobina: 1, quantity: 3, to_install: '50.00',
      precio_compra_mtr_lineal: '80.00', precio_venta_mtr_lineal: '120.00',
    });

    component.save();

    const req = httpMock.expectOne(`${base}/inventario`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body.sucursal).toBe(1);
    expect(req.request.body.bobina).toBe(1);
    req.flush({
      id: 5, sucursal: 1, sucursal_name: 'Central', bobina: 1, window_film_name: 'Carbon 20%',
      bobina_width: '1.50', quantity: 3, to_install: '50.00', installed: '0.00',
      original_length: '50.00', date: '2026-09-27T00:00:00Z', numero_referencia: 0,
      precio_compra_mtr_lineal: '80.00', precio_venta_mtr_lineal: '120.00', nro_lote: null,
      is_active: true,
    });
  });

  it('muestra el error del backend cuando la creacion falla', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;
    component.form.patchValue({
      sucursal: 1, bobina: 1, quantity: 3, to_install: '50.00',
      precio_compra_mtr_lineal: '80.00', precio_venta_mtr_lineal: '120.00',
    });

    component.save();

    httpMock
      .expectOne(`${base}/inventario`)
      .flush({ bobina: ['Clave primaria invalida.'] }, { status: 400, statusText: 'Bad Request' });

    expect(component.errorMessage).toBe('Clave primaria invalida.');
    expect(component.saving).toBe(false);
  });
});
