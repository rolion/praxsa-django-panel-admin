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
const twoSucursales: AppSucursal[] = [
  { id: 1, name: 'Central' },
  { id: 2, name: 'Norte' },
];
const sampleBobinas: AppWindowFilmReel[] = [
  { id: 1, window_film: 1, window_film_name: 'Carbon 20%', width: '1.50', length: '30.00', price: '120.00', is_active: true },
];

describe('InventarioCreateComponent', () => {
  let httpMock: HttpTestingController;
  const base = `${environment.apiUrl}/product/almacen`;

  function createAndLoad(sucursales: AppSucursal[] = sampleSucursales) {
    const fixture = TestBed.createComponent(InventarioCreateComponent);
    fixture.detectChanges();
    httpMock.expectOne(`${base}/sucursales`).flush(sucursales);
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
      precio_compra_mtr_lineal: '80.00', precio_venta_mtr_lineal: '120.00', nro_lote: 'L001',
    });

    component.save();

    const req = httpMock.expectOne(`${base}/inventario`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body.sucursal).toBe(1);
    expect(req.request.body.bobina).toBe(1);
    expect(req.request.body.nro_lote).toBe('L001');
    expect(req.request.body.date).toBeUndefined();
    req.flush({
      id: 5, sucursal: 1, sucursal_name: 'Central', bobina: 1, window_film_name: 'Carbon 20%',
      bobina_width: '1.50', quantity: 3, to_install: '50.00', installed: '0.00',
      original_length: '50.00', date: '2026-09-27T00:00:00Z', numero_referencia: 0,
      precio_compra_mtr_lineal: '80.00', precio_venta_mtr_lineal: '120.00', nro_lote: 'L001',
      is_active: true,
    });
  });

  it('envia la fecha cuando se completa el campo', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;
    component.form.patchValue({
      sucursal: 1, bobina: 1, quantity: 3, to_install: '50.00',
      precio_compra_mtr_lineal: '80.00', precio_venta_mtr_lineal: '120.00', nro_lote: 'L001',
      date: '2026-09-20',
    });

    component.save();

    const req = httpMock.expectOne(`${base}/inventario`);
    expect(req.request.body.date).toBe('2026-09-20');
    req.flush({
      id: 6, sucursal: 1, sucursal_name: 'Central', bobina: 1, window_film_name: 'Carbon 20%',
      bobina_width: '1.50', quantity: 3, to_install: '50.00', installed: '0.00',
      original_length: '50.00', date: '2026-09-20T00:00:00Z', numero_referencia: 0,
      precio_compra_mtr_lineal: '80.00', precio_venta_mtr_lineal: '120.00', nro_lote: 'L001',
      is_active: true,
    });
  });

  it('no envia el formulario sin nro_lote (obligatorio)', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;
    component.form.patchValue({
      sucursal: 1, bobina: 1, quantity: 3, to_install: '50.00',
      precio_compra_mtr_lineal: '80.00', precio_venta_mtr_lineal: '120.00', nro_lote: '',
    });

    component.save();

    httpMock.expectNone(`${base}/inventario`);
    expect(component.form.get('nro_lote')?.hasError('required')).toBe(true);
  });

  it('no envia el formulario con un nro_lote no alfanumerico', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;
    component.form.patchValue({
      sucursal: 1, bobina: 1, quantity: 3, to_install: '50.00',
      precio_compra_mtr_lineal: '80.00', precio_venta_mtr_lineal: '120.00', nro_lote: 'L-999',
    });

    component.save();

    httpMock.expectNone(`${base}/inventario`);
    expect(component.form.get('nro_lote')?.hasError('pattern')).toBe(true);
  });

  it('no envia el formulario con un nro_lote de mas de 15 caracteres', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;
    component.form.patchValue({
      sucursal: 1, bobina: 1, quantity: 3, to_install: '50.00',
      precio_compra_mtr_lineal: '80.00', precio_venta_mtr_lineal: '120.00', nro_lote: 'X'.repeat(20),
    });

    component.save();

    httpMock.expectNone(`${base}/inventario`);
    expect(component.form.get('nro_lote')?.hasError('maxlength')).toBe(true);
  });

  it('muestra el error del backend cuando la creacion falla', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;
    component.form.patchValue({
      sucursal: 1, bobina: 1, quantity: 3, to_install: '50.00',
      precio_compra_mtr_lineal: '80.00', precio_venta_mtr_lineal: '120.00', nro_lote: 'L001',
    });

    component.save();

    httpMock
      .expectOne(`${base}/inventario`)
      .flush({ bobina: ['Clave primaria invalida.'] }, { status: 400, statusText: 'Bad Request' });

    expect(component.errorMessage).toBe('Clave primaria invalida.');
    expect(component.saving).toBe(false);
  });

  it('con una sola sucursal la deja preseleccionada y bloqueada, y la envia igual', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;

    expect(component.form.get('sucursal')?.value).toBe(1);
    expect(component.form.get('sucursal')?.disabled).toBe(true);

    component.form.patchValue({
      bobina: 1, quantity: 3, to_install: '50.00',
      precio_compra_mtr_lineal: '80.00', precio_venta_mtr_lineal: '120.00', nro_lote: 'L001',
    });
    component.save();

    const req = httpMock.expectOne(`${base}/inventario`);
    expect(req.request.body.sucursal).toBe(1);
    req.flush({
      id: 9, sucursal: 1, sucursal_name: 'Central', bobina: 1, window_film_name: 'Carbon 20%',
      bobina_width: '1.50', quantity: 3, to_install: '50.00', installed: '0.00',
      original_length: '50.00', date: '2026-09-27T00:00:00Z', numero_referencia: 0,
      precio_compra_mtr_lineal: '80.00', precio_venta_mtr_lineal: '120.00', nro_lote: 'L001',
      is_active: true,
    });
  });

  it('solo ofrece las sucursales activas (las inactivas son de solo lectura)', () => {
    const fixture = createAndLoad([
      { id: 1, name: 'Central', activa: true },
      { id: 2, name: 'Norte', activa: false },
      { id: 3, name: 'Sur', activa: true },
    ]);
    const component = fixture.componentInstance;

    expect(component.sucursales.map((s) => s.id)).toEqual([1, 3]);
    expect(component.form.get('sucursal')?.value).toBeNull();
  });

  it('con una sola activa (y otra inactiva) la deja preseleccionada y bloqueada', () => {
    const fixture = createAndLoad([
      { id: 1, name: 'Central', activa: true },
      { id: 2, name: 'Norte', activa: false },
    ]);

    expect(fixture.componentInstance.form.get('sucursal')?.value).toBe(1);
    expect(fixture.componentInstance.form.get('sucursal')?.disabled).toBe(true);
  });

  it('sin sucursales activas avisa y no hay nada que elegir', () => {
    const fixture = createAndLoad([{ id: 2, name: 'Norte', activa: false }]);

    expect(fixture.componentInstance.withoutActiveSucursales).toBe(true);
    expect(fixture.componentInstance.sucursales).toEqual([]);
  });

  it('con varias sucursales las ofrece todas y no preselecciona ninguna', () => {
    const fixture = createAndLoad(twoSucursales);
    const component = fixture.componentInstance;

    expect(component.sucursales).toEqual(twoSucursales);
    expect(component.form.get('sucursal')?.value).toBeNull();
    expect(component.form.get('sucursal')?.enabled).toBe(true);
  });
});
