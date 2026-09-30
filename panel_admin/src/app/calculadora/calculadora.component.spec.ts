import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { AuthService } from '@core';
import { environment } from '../../environments/environment';
import { OrdenSucursal, ReelCatalogItem } from '../ordenes/ordenes.model';
import { AppCarBrand, AppCarModel, AppCarModelPart } from '../vehicles/vehicles.model';
import { CalculadoraComponent } from './calculadora.component';

const ordenes = `${environment.apiUrl}/product/ordenes`;
const vehicles = `${environment.apiUrl}/product/vehicles`;

const sucursal: OrdenSucursal = { id: 1, name: 'Central', address: 'x' };
const brands: AppCarBrand[] = [{ id: 1, name: 'Toyota', is_active: true, models_count: 1 }];
const models: AppCarModel[] = [
  { id: 9, name: 'Hilux', car_brand_id: 1, car_brand_name: 'Toyota', image: null, is_active: true, items_count: 2 },
];
const parts: AppCarModelPart[] = [
  { id: 1, car_part_id: 5, car_part_name: 'Parabrisas', width: '1.50', length: '1.20', quantity: 2, installation_price: '50.00' },
  { id: 2, car_part_id: 6, car_part_name: 'Puerta delantera izquierda', width: '0.90', length: '1.00', quantity: 1, installation_price: '20.00' },
];
const reels: ReelCatalogItem[] = [
  { window_film: 3, window_film_name: 'Carbon', width: '1.50', available_meters: '50.00', unit_price: '120.00' },
  { window_film: 4, window_film_name: 'Basica', width: '1.00', available_meters: '10.00', unit_price: '90.00' },
];

describe('CalculadoraComponent', () => {
  let fixture: ComponentFixture<CalculadoraComponent>;
  let component: CalculadoraComponent;
  let httpMock: HttpTestingController;
  let router: Router;
  let allowCreate = true;

  function setup(sucursales: OrdenSucursal[] = [sucursal]) {
    TestBed.configureTestingModule({
      imports: [CalculadoraComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    httpMock = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    spyOn(TestBed.inject(AuthService), 'hasPermission').and.callFake(() => allowCreate);
    fixture = TestBed.createComponent(CalculadoraComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    httpMock.expectOne(`${ordenes}/catalogo/sucursales`).flush(sucursales);
    httpMock.expectOne(`${vehicles}/brands`).flush(brands);
    fixture.detectChanges();
  }

  function pickModel(items: AppCarModelPart[] = parts, reelList: ReelCatalogItem[] = reels) {
    component.filters.get('brand')?.setValue(1);
    component.onBrandChange();
    httpMock.expectOne((r) => r.url === `${vehicles}/models`).flush(models);
    component.filters.get('model')?.setValue(9);
    component.onModelChange();
    fixture.detectChanges();
    httpMock.expectOne(`${vehicles}/models/9/items/`).flush(items);
    httpMock.expectOne((r) => r.url === `${ordenes}/catalogo/bobinas`).flush(reelList);
    fixture.detectChanges();
  }

  const text = () => (fixture.nativeElement as HTMLElement).textContent ?? '';
  const total = () => (fixture.nativeElement as HTMLElement).querySelector('[data-testid="total"]')?.textContent?.trim();

  beforeEach(() => {
    allowCreate = true;
  });

  afterEach(() => httpMock.verify());

  it('starts in the initial state with step 1 and disabled actions', () => {
    setup();
    expect(component.state()).toBe('initial');
    expect(component.step()).toBe(1);
    expect(text()).toContain('Selecciona sucursal, marca y modelo');
    expect(total()).toBe('Bs 0');
    expect(component.canAct).toBeFalse();
  });

  it('fixes the only sucursal (read only)', () => {
    setup();
    expect(component.filters.getRawValue().sucursal).toBe(1);
    expect(component.filters.get('sucursal')?.disabled).toBeTrue();
  });

  it('warns when the user has no sucursal', () => {
    setup([]);
    expect(text()).toContain('Asigne una sucursal');
  });

  it('keeps the model select disabled until a brand loads its models', () => {
    setup();
    expect(component.filters.get('model')?.disabled).toBeTrue();
    component.filters.get('brand')?.setValue(1);
    component.onBrandChange();
    const req = httpMock.expectOne((r) => r.url === `${vehicles}/models`);
    expect(req.request.params.get('car_brand_id')).toBe('1');
    req.flush(models);
    expect(component.filters.get('model')?.enabled).toBeTrue();
    expect(component.models().length).toBe(1);
  });

  it('shows skeletons while loading and then the active table at step 2', () => {
    setup();
    component.filters.get('brand')?.setValue(1);
    component.onBrandChange();
    httpMock.expectOne((r) => r.url === `${vehicles}/models`).flush(models);
    component.filters.get('model')?.setValue(9);
    component.onModelChange();
    fixture.detectChanges();
    expect(component.state()).toBe('loading');
    expect((fixture.nativeElement as HTMLElement).querySelector('[data-state="loading"]')).not.toBeNull();
    httpMock.expectOne(`${vehicles}/models/9/items/`).flush(parts);
    httpMock.expectOne((r) => r.url === `${ordenes}/catalogo/bobinas`).flush(reels);
    fixture.detectChanges();

    expect(component.state()).toBe('active');
    expect(component.step()).toBe(2);
    expect(text()).toContain('Parabrisas');
    expect(text()).toContain('1.50 × 1.20 m · Cantidad 2');
  });

  it('only offers films wide enough and with stock, cheapest first', () => {
    setup();
    pickModel();
    // Parabrisas (1.50): solo Carbon. Puerta (0.90): Basica (90) y Carbon (120).
    expect(component.optionsByItem()[0].map((o) => o.name)).toEqual(['Carbon']);
    expect(component.optionsByItem()[1].map((o) => o.name)).toEqual(['Basica', 'Carbon']);
  });

  it('recalculates the item subtotals and the total when a film is chosen or changed', () => {
    setup();
    pickModel();
    component.line(0).get('reel')?.setValue('3|1.50'); // 1.20 x 2 x 120 + 50 x 2 = 388
    component.line(1).get('reel')?.setValue('4|1.00'); // 1.00 x 1 x 90 + 20 x 1 = 110
    fixture.detectChanges();

    expect(component.quote().lines.map((l) => l.subtotal)).toEqual([388, 110]);
    expect(component.quote().total).toBe(498);
    expect(total()).toBe('Bs 498');

    component.line(1).get('reel')?.setValue('3|1.50'); // 1.00 x 1 x 120 + 20 = 140
    expect(component.quote().total).toBe(528);
  });

  it('excludes an item from the total and restores it', () => {
    setup();
    pickModel();
    component.line(0).get('reel')?.setValue('3|1.50');
    component.line(1).get('reel')?.setValue('4|1.00');

    component.toggleExcluded(0);
    expect(component.isExcluded(0)).toBeTrue();
    expect(component.quote().total).toBe(110);
    expect(component.line(0).get('reel')?.disabled).toBeTrue();

    component.toggleExcluded(0);
    expect(component.isExcluded(0)).toBeFalse();
    expect(component.quote().total).toBe(498);
    expect(component.line(0).get('reel')?.enabled).toBeTrue();
  });

  it('shows the empty state when the model has no items', () => {
    setup();
    pickModel([], reels);
    expect(component.state()).toBe('empty');
    expect(text()).toContain('no tiene ítems configurados');
  });

  it('shows the empty state when the sucursal has no reels', () => {
    setup();
    pickModel(parts, []);
    expect(component.state()).toBe('empty');
    expect(text()).toContain('No hay láminas con stock');
  });

  it('warns on a row when no reel fits the item', () => {
    setup();
    pickModel(parts, [reels[1]]); // solo 1.00: el parabrisas (1.50) no tiene lamina apta
    expect(component.noOptionsWarning(0)).toContain('mínimo 1.50 m');
    expect(component.noOptionsWarning(1)).toBeNull();
  });

  it('shows the error state and retries the load', () => {
    setup();
    component.filters.get('brand')?.setValue(1);
    component.onBrandChange();
    httpMock.expectOne((r) => r.url === `${vehicles}/models`).flush(models);
    component.filters.get('model')?.setValue(9);
    component.onModelChange();
    httpMock.expectOne(`${vehicles}/models/9/items/`).flush('x', { status: 500, statusText: 'err' });
    // forkJoin cancela la otra peticion al fallar la primera.
    httpMock.match((r) => r.url === `${ordenes}/catalogo/bobinas`);
    fixture.detectChanges();
    expect(component.state()).toBe('error');

    component.retry();
    httpMock.expectOne(`${vehicles}/models/9/items/`).flush(parts);
    httpMock.expectOne((r) => r.url === `${ordenes}/catalogo/bobinas`).flush(reels);
    expect(component.state()).toBe('active');
  });

  it('enables the actions only when at least one item has a film', () => {
    setup();
    pickModel();
    expect(component.canAct).toBeFalse();
    component.line(0).get('reel')?.setValue('3|1.50');
    expect(component.canAct).toBeTrue();
  });

  it('builds a wa.me link with the vehicle, priced items and total', () => {
    setup();
    pickModel();
    component.line(0).get('reel')?.setValue('3|1.50');
    const url = decodeURIComponent(component.whatsappUrl);
    expect(component.whatsappUrl.startsWith('https://wa.me/59178181012?text=')).toBeTrue();
    expect(url).toContain('Vehiculo: Toyota Hilux');
    expect(url).toContain('Parabrisas: Carbon (Bs 388)');
    expect(url).toContain('Total referencial: Bs 388');
  });

  it('hides "Crear Proforma" without the add_proforma_header permission', () => {
    allowCreate = false;
    setup();
    pickModel();
    expect(text()).not.toContain('Crear Proforma');
    expect(text()).toContain('Consultar por WhatsApp');
  });

  it('opens the proforma form with the quote as navigation state (priced, non-excluded items only)', () => {
    setup();
    pickModel();
    component.line(0).get('reel')?.setValue('3|1.50');
    component.line(1).get('reel')?.setValue('4|1.00');
    component.toggleExcluded(1);
    expect(text()).toContain('Crear Proforma');

    component.createProforma();

    expect(component.step()).toBe(3);
    expect(router.navigate).toHaveBeenCalledWith(['/ordenes/proformas/create'], {
      state: {
        cotizacion: {
          version: 1,
          sucursal: 1,
          carModelId: 9,
          lines: [{ carPartId: 5, windowFilm: 3, width: '1.50', length: '1.20', quantity: 2 }],
        },
      },
    });
  });

  it('does not navigate without the permission or without priced items', () => {
    allowCreate = false;
    setup();
    pickModel();
    component.line(0).get('reel')?.setValue('3|1.50');
    component.createProforma();
    expect(router.navigate).not.toHaveBeenCalled();
  });
});
