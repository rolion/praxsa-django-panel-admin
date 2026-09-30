import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AppCarModel, AppCarModelPart } from '../../vehicles/vehicles.model';
import { AppProformaDetail, OrdenSucursal, ReelCatalogItem } from '../ordenes.model';
import { ProformaFormComponent } from './proforma-form.component';

const ordenes = `${environment.apiUrl}/product/ordenes`;
const vehicles = `${environment.apiUrl}/product/vehicles`;

const sucursal: OrdenSucursal = { id: 1, name: 'Central', address: 'x' };
const models: AppCarModel[] = [
  { id: 9, name: 'Corolla', car_brand_id: 1, car_brand_name: 'Toyota', image: null, is_active: true, items_count: 1 },
];
const parts: AppCarModelPart[] = [
  { id: 1, car_part_id: 5, car_part_name: 'Parabrisas', width: '1.50', length: '1.20', quantity: 2, installation_price: '50.00' },
];
const reels: ReelCatalogItem[] = [
  { window_film: 3, window_film_name: 'Carbon', width: '1.50', available_meters: '50.00', unit_price: '120.00' },
  { window_film: 3, window_film_name: 'Carbon', width: '1.00', available_meters: '10.00', unit_price: '90.00' },
];

describe('ProformaFormComponent', () => {
  let component: ProformaFormComponent;
  let httpMock: HttpTestingController;
  let router: Router;

  function setup(id?: string) {
    TestBed.configureTestingModule({
      imports: [ProformaFormComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap(id ? { id } : {}) } } },
      ],
    });
    httpMock = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    const fixture = TestBed.createComponent(ProformaFormComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    httpMock.expectOne(`${vehicles}/models`).flush(models);
  }

  /** Alta con una sola sucursal: queda fija y se carga su catalogo de bobinas. */
  function setupCreate() {
    setup();
    httpMock.expectOne(`${ordenes}/catalogo/sucursales`).flush([sucursal]);
    httpMock.expectOne((r) => r.url === `${ordenes}/catalogo/bobinas`).flush(reels);
  }

  afterEach(() => httpMock.verify());

  function fillCustomer(): void {
    component.form.patchValue({
      name: 'Ana', email: 'ana@test.com', ci_nit: '123', phone_number: '70000001',
    });
  }

  it('fixes the sucursal (read only) when the user has only one and loads its reels', () => {
    setupCreate();
    expect(component.form.getRawValue().sucursal).toBe(1);
    expect(component.form.get('sucursal')?.disabled).toBe(true);
    expect(component.reels.length).toBe(2);
  });

  it('shows a message when the user has no sucursal', () => {
    setup();
    httpMock.expectOne(`${ordenes}/catalogo/sucursales`).flush([]);
    expect(component.errorMessage).toContain('Asigne una sucursal');
  });

  it('venta con instalacion requires model, plate and an item; metro lineal does not', () => {
    setupCreate();
    expect(component.form.get('car_model_id')?.valid).toBe(false);
    expect(component.form.get('car_plate')?.valid).toBe(false);
    expect(component.lines.at(0).get('car_part')?.valid).toBe(false);

    component.form.get('sales_type')?.setValue('venta_metro_lineal');

    expect(component.form.get('car_model_id')?.valid).toBe(true);
    expect(component.form.get('car_plate')?.valid).toBe(true);
    expect(component.lines.length).toBe(1);
    expect(component.lines.at(0).get('car_part')?.valid).toBe(true);
    expect(component.lines.at(0).get('quantity')?.valid).toBe(true);
  });

  it('metro lineal shows the model as optional, sends it when chosen and keeps the reference panel', () => {
    setupCreate();
    component.form.get('sales_type')?.setValue('venta_metro_lineal');
    fillCustomer();
    component.form.patchValue({ car_model_id: 9 });
    component.onModelChange();
    httpMock.expectOne(`${vehicles}/models/9/items/`).flush(parts);
    component.lines.at(0).patchValue({ reel: component.reelKey(3, '1.50'), length: '3.5' });

    expect(component.form.get('car_model_id')?.valid).toBe(true);
    expect(component.hasReference).toBe(true);

    component.save();

    const req = httpMock.expectOne(`${ordenes}/proformas`);
    expect(req.request.body.car_model_id).toBe(9);
    expect(req.request.body.items).toEqual([{ window_film: 3, width: '1.50', length: '3.5' }]);
    req.flush({ id: 50 });
  });

  it('switching the sales type keeps the selected model and its reference items', () => {
    setupCreate();
    component.form.patchValue({ car_model_id: 9 });
    component.onModelChange();
    httpMock.expectOne(`${vehicles}/models/9/items/`).flush(parts);

    component.form.get('sales_type')?.setValue('venta_metro_lineal');

    expect(component.form.get('car_model_id')?.value).toBe(9);
    expect(component.items.length).toBe(1);
  });

  it('the reference panel needs a model with items, can be collapsed and copies the measure', async () => {
    setupCreate();
    expect(component.hasReference).toBe(false);
    component.form.patchValue({ car_model_id: 9 });
    component.onModelChange();
    httpMock.expectOne(`${vehicles}/models/9/items/`).flush(parts);
    expect(component.hasReference).toBe(true);

    expect(component.showReference).toBe(true);
    component.toggleReference();
    expect(component.showReference).toBe(false);

    const write = jasmine.createSpy('writeText').and.returnValue(Promise.resolve());
    spyOnProperty(navigator, 'clipboard', 'get').and.returnValue({ writeText: write } as unknown as Clipboard);
    component.copyMeasure(parts[0]);
    await Promise.resolve();
    expect(write).toHaveBeenCalledWith('1.50 x 1.20');
    expect(component.copiedItemId).toBe(1);
  });

  it('the detail table has 9 columns for instalacion and 6 for metro lineal', () => {
    setupCreate();
    expect(component.columnCount).toBe(9);
    component.form.get('sales_type')?.setValue('venta_metro_lineal');
    expect(component.columnCount).toBe(6);
  });

  it('picking an item preloads length and quantity, picking a reel gives width and price', () => {
    setupCreate();
    component.form.patchValue({ car_model_id: 9 });
    component.onModelChange();
    httpMock.expectOne(`${vehicles}/models/9/items/`).flush(parts);
    const line = component.lines.at(0);

    line.patchValue({ car_part: 5 });
    component.onItemChange(0);
    line.patchValue({ reel: component.reelKey(3, '1.50') });

    expect(line.get('length')?.value).toBe('1.20');
    expect(line.get('quantity')?.value).toBe(2);
    expect(component.reelOf(0)?.width).toBe('1.50');
    // 1.20 * 2 * 120 + 50 * 2
    expect(component.lineSubtotal(0)).toBe(388);
    expect(component.total).toBe(388);
    expect(component.totalAPagar).toBe(388);
  });

  it('warns when the reel is narrower than the item, and about stock', () => {
    setupCreate();
    component.form.patchValue({ car_model_id: 9 });
    component.onModelChange();
    httpMock.expectOne(`${vehicles}/models/9/items/`).flush(parts);
    const line = component.lines.at(0);
    line.patchValue({ car_part: 5, reel: component.reelKey(3, '1.00'), length: '6', quantity: 2 });

    expect(component.widthWarning(0)).toContain('1.50');
    expect(component.stockWarning(0)).toContain('10.00');
  });

  it('metro lineal preview is metros x price with no item, quantity or installation', () => {
    setupCreate();
    component.form.get('sales_type')?.setValue('venta_metro_lineal');
    component.lines.at(0).patchValue({ reel: component.reelKey(3, '1.50'), length: '3.5' });

    expect(component.lineSubtotal(0)).toBe(420);
  });

  it('validates the discount against the previewed total', () => {
    setupCreate();
    component.form.get('sales_type')?.setValue('venta_metro_lineal');
    component.lines.at(0).patchValue({ reel: component.reelKey(3, '1.50'), length: '3.5' }); // 420

    component.form.patchValue({ discount: '211' });
    expect(component.discountError).toContain('50%');
    component.form.patchValue({ discount: '10', discount_reason: '' });
    expect(component.discountError).toContain('motivo');
    component.form.patchValue({ discount: '10', discount_reason: 'cliente frecuente' });
    expect(component.discountError).toBeNull();
    expect(component.totalAPagar).toBe(410);
  });

  it('mirrors the model validators (email, phone)', () => {
    setupCreate();
    component.form.patchValue({ email: 'no-es-email', phone_number: 'abc' });
    expect(component.form.get('email')?.valid).toBe(false);
    expect(component.form.get('phone_number')?.valid).toBe(false);
    fillCustomer();
    expect(component.form.get('email')?.valid).toBe(true);
    expect(component.form.get('phone_number')?.valid).toBe(true);
  });

  it('does not submit an invalid form', () => {
    setupCreate();
    component.save();
    httpMock.expectNone(`${ordenes}/proformas`);
    expect(component.submitted).toBe(true);
  });

  it('creates a metro lineal proforma sending only what the person chose', () => {
    setupCreate();
    component.form.get('sales_type')?.setValue('venta_metro_lineal');
    fillCustomer();
    component.lines.at(0).patchValue({ reel: component.reelKey(3, '1.50'), length: '3.5' });

    component.save();

    const req = httpMock.expectOne(`${ordenes}/proformas`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body.sales_type).toBe('venta_metro_lineal');
    expect(req.request.body.sucursal).toBe(1);
    expect(req.request.body.car_model_id).toBeNull();
    expect(req.request.body.items).toEqual([{ window_film: 3, width: '1.50', length: '3.5' }]);
    expect(req.request.body.total_price).toBeUndefined();
    req.flush({ id: 44 });
    expect(router.navigate).toHaveBeenCalledWith(['/ordenes/proformas/view', 44]);
  });

  it('creates a venta con instalacion proforma with item and quantity', () => {
    setupCreate();
    fillCustomer();
    component.form.patchValue({ car_model_id: 9, car_plate: 'ABC123' });
    component.onModelChange();
    httpMock.expectOne(`${vehicles}/models/9/items/`).flush(parts);
    component.lines.at(0).patchValue({ car_part: 5, reel: component.reelKey(3, '1.50') });
    component.onItemChange(0);

    component.save();

    const req = httpMock.expectOne(`${ordenes}/proformas`);
    expect(req.request.body.car_model_id).toBe(9);
    expect(req.request.body.items).toEqual([
      { window_film: 3, width: '1.50', length: '1.20', car_part: 5, quantity: 2 },
    ]);
    req.flush({ id: 45 });
  });

  it('shows the server errors when saving fails', () => {
    setupCreate();
    component.form.get('sales_type')?.setValue('venta_metro_lineal');
    fillCustomer();
    component.lines.at(0).patchValue({ reel: component.reelKey(3, '1.50'), length: '3.5' });

    component.save();
    httpMock
      .expectOne(`${ordenes}/proformas`)
      .flush({ items: ['Línea 1: No hay bobina'] }, { status: 400, statusText: 'Bad Request' });

    expect(component.errorMessage).toBe('Línea 1: No hay bobina');
    expect(component.saving).toBe(false);
  });

  it('changing the sucursal reloads the reels and clears selected ones', () => {
    setup();
    httpMock.expectOne(`${ordenes}/catalogo/sucursales`).flush([sucursal, { id: 2, name: 'Norte', address: 'y' }]);
    component.form.get('sucursal')?.setValue(1);
    component.onSucursalChange();
    httpMock.expectOne((r) => r.url === `${ordenes}/catalogo/bobinas`).flush(reels);
    component.lines.at(0).patchValue({ reel: component.reelKey(3, '1.50') });

    component.form.get('sucursal')?.setValue(2);
    component.onSucursalChange();
    httpMock
      .expectOne((r) => r.url === `${ordenes}/catalogo/bobinas` && r.params.get('sucursal') === '2')
      .flush([reels[1]]);

    expect(component.lines.at(0).get('reel')?.value).toBeNull();
    expect(component.infoMessage).toContain('bobinas');
  });

  describe('edit mode', () => {
    const proforma = {
      id: 5, sales_type: 'venta_instalacion', sales_type_label: 'Venta con Instalación', name: 'Ana',
      sucursal: 1, sucursal_name: 'Central', car_model_name: 'Corolla', car_brand_name: 'Toyota',
      car_plate: 'ABC123', total_price: '388.00', discount: '0.00', total_a_pagar: '388.00',
      proforma_created_on: '2026-09-29T10:00:00', status: 'proforma', status_label: 'Proforma',
      is_close: false, nota_trabajo_id: null, nota_venta_id: null, email: 'ana@test.com', ci_nit: '123',
      phone_number: '70000001', car_model_id: 9, discount_reason: '',
      items: [{
        id: 1, car_part: 5, car_part_name: 'Parabrisas', window_film: 3, window_film_name: 'Carbon',
        width: '1.50', length: '1.20', quantity: 2, window_film_price: '120.00',
        installation_price: '50.00', sub_total: '388.00',
      }],
    } as AppProformaDetail;

    function setupEdit(detail: AppProformaDetail) {
      setup('5');
      httpMock.expectOne(`${ordenes}/catalogo/sucursales`).flush([sucursal]);
      httpMock.expectOne(`${ordenes}/proformas/5/`).flush(detail);
    }

    it('preloads the proforma and locks sales type and sucursal', () => {
      setupEdit(proforma);
      httpMock.expectOne((r) => r.url === `${ordenes}/catalogo/bobinas`).flush(reels);
      httpMock.expectOne(`${vehicles}/models/9/items/`).flush(parts);

      expect(component.isEdit).toBe(true);
      expect(component.form.get('sales_type')?.disabled).toBe(true);
      expect(component.form.get('sucursal')?.disabled).toBe(true);
      expect(component.form.value.name).toBe('Ana');
      expect(component.lines.length).toBe(1);
      expect(component.reelOf(0)?.unit_price).toBe('120.00');
      expect(component.total).toBe(388);
    });

    it('keeps the saved reels when the catalog width arrives as a number (1.5) and the line as "1.50"', () => {
      setupEdit(proforma);
      const numericCatalog = [
        { window_film: 3, window_film_name: 'Carbon', width: 1.5, available_meters: 50, unit_price: 120 },
      ] as unknown as ReelCatalogItem[];
      httpMock.expectOne((r) => r.url === `${ordenes}/catalogo/bobinas`).flush(numericCatalog);
      httpMock.expectOne(`${vehicles}/models/9/items/`).flush(parts);

      expect(component.lines.at(0).get('reel')?.value).toBe('3|1.50');
      expect(component.reelOf(0)).toBeDefined();
      expect(component.infoMessage).toBe('');
      expect(component.total).toBe(388);
    });

    it('sends the width of the reel with 2 decimals', () => {
      setupEdit(proforma);
      httpMock.expectOne((r) => r.url === `${ordenes}/catalogo/bobinas`).flush(reels);
      httpMock.expectOne(`${vehicles}/models/9/items/`).flush(parts);

      component.save();

      const req = httpMock.expectOne(`${ordenes}/proformas/5/`);
      expect(req.request.body.items[0].width).toBe('1.50');
      req.flush(proforma);
    });

    it('sends a PATCH without sales type or sucursal', () => {
      setupEdit(proforma);
      httpMock.expectOne((r) => r.url === `${ordenes}/catalogo/bobinas`).flush(reels);
      httpMock.expectOne(`${vehicles}/models/9/items/`).flush(parts);

      component.save();

      const req = httpMock.expectOne(`${ordenes}/proformas/5/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body.sales_type).toBeUndefined();
      expect(req.request.body.sucursal).toBeUndefined();
      expect(req.request.body.items.length).toBe(1);
      req.flush(proforma);
      expect(router.navigate).toHaveBeenCalledWith(['/ordenes/proformas/view', 5]);
    });

    it('redirects to the view when the proforma is already closed', () => {
      setupEdit({ ...proforma, is_close: true });
      expect(router.navigate).toHaveBeenCalledWith(['/ordenes/proformas/view', 5]);
    });
  });
});
