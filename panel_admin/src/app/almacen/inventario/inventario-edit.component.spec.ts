import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AppInventario } from '../almacen.model';
import { InventarioEditComponent } from './inventario-edit.component';

const sampleInventario: AppInventario = {
  id: 7, sucursal: 1, sucursal_name: 'Central', sucursal_activa: true, bobina: 1, window_film_name: 'Carbon 20%',
  bobina_width: '1.50', quantity: 3, to_install: '50.00', installed: '0.00',
  original_length: '50.00', date: '2026-09-27T00:00:00Z', numero_referencia: 0,
  precio_compra_mtr_lineal: '80.00', precio_venta_mtr_lineal: '120.00', nro_lote: 'L1',
  is_active: true,
};

describe('InventarioEditComponent', () => {
  let httpMock: HttpTestingController;
  const base = `${environment.apiUrl}/product/almacen/inventario`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [InventarioEditComponent],
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

  function createAndLoad() {
    const fixture = TestBed.createComponent(InventarioEditComponent);
    fixture.detectChanges();
    httpMock.expectOne(`${base}/7/`).flush(sampleInventario);
    return fixture;
  }

  it('una sucursal inactiva deja el formulario de solo lectura y no guarda', () => {
    const fixture = TestBed.createComponent(InventarioEditComponent);
    fixture.detectChanges();
    httpMock.expectOne(`${base}/7/`).flush({ ...sampleInventario, sucursal_activa: false });
    const component = fixture.componentInstance;

    expect(component.sucursalInactiva).toBe(true);
    expect(component.form.disabled).toBe(true);

    component.save();
    httpMock.expectNone(`${base}/7/`);
  });

  it('carga los datos existentes en el formulario', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;

    expect(component.form.value.to_install).toBe('50.00');
    expect(component.form.value.nro_lote).toBe('L1');
  });

  it('save() envia solo los campos permitidos', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;
    component.form.patchValue({ to_install: '25.00' });

    component.save();

    const req = httpMock.expectOne(`${base}/7/`);
    expect(req.request.body).toEqual({
      to_install: '25.00', installed: '0.00', precio_compra_mtr_lineal: '80.00',
      precio_venta_mtr_lineal: '120.00', nro_lote: 'L1',
    });
    req.flush(sampleInventario);
  });

  it('muestra el error del backend cuando falla', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;

    component.save();

    httpMock
      .expectOne(`${base}/7/`)
      .flush({ to_install: ['Valor invalido.'] }, { status: 400, statusText: 'Bad Request' });

    expect(component.errorMessage).toBe('Valor invalido.');
    expect(component.saving).toBe(false);
  });
});
