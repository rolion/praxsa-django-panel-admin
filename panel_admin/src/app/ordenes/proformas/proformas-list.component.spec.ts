import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/service/auth.service';
import { AppProforma } from '../ordenes.model';
import Swal, { SweetAlertResult } from 'sweetalert2';
import { ProformasListComponent } from './proformas-list.component';

const row = (overrides: Partial<AppProforma> = {}): AppProforma => ({
  id: 1, sales_type: 'venta_instalacion', sales_type_label: 'Venta con Instalación', name: 'Ana',
  sucursal: 1, sucursal_name: 'Central', car_model_name: 'Corolla', car_brand_name: 'Toyota',
  car_plate: 'ABC123', total_price: '340.00', discount: '0.00', total_a_pagar: '340.00',
  proforma_created_on: '2026-09-29T10:00:00', status: 'proforma', status_label: 'Proforma',
  is_close: false, nota_trabajo_id: null, ...overrides,
});

describe('ProformasListComponent', () => {
  let component: ProformasListComponent;
  let httpMock: HttpTestingController;
  let authService: AuthService;
  const base = `${environment.apiUrl}/product/ordenes`;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [ProformasListComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    httpMock = TestBed.inject(HttpTestingController);
    authService = TestBed.inject(AuthService);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  function login(permissions: string[]): void {
    authService.login('u', 'p').subscribe();
    httpMock.expectOne(`${environment.apiUrl}/product/api-panel-admin-token-auth/`).flush({
      token: 't', user_id: 1, username: 'u', name: 'U', lastname: 'U', is_staff: true, groups: [], permissions,
    });
  }

  function create(rows: AppProforma[]) {
    const fixture = TestBed.createComponent(ProformasListComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    httpMock.expectOne(`${base}/proformas`).flush(rows);
    return fixture;
  }

  it('loads the rows and filters client side by number, client, plate and model', () => {
    create([row(), row({ id: 2, name: 'Luis', car_plate: 'ZZZ999', car_model_name: 'Hilux' })]);
    expect(component.rows.length).toBe(2);

    component.filterDatatable({ target: { value: 'zzz' } } as unknown as Event);
    expect(component.rows.map((r) => r.id)).toEqual([2]);
    component.filterDatatable({ target: { value: 'corolla' } } as unknown as Event);
    expect(component.rows.map((r) => r.id)).toEqual([1]);
    component.filterDatatable({ target: { value: 'hilux' } } as unknown as Event);
    expect(component.rows.map((r) => r.id)).toEqual([2]);
  });

  it('derives the action permissions from the effective permissions', () => {
    login(['product.add_proforma_header', 'product.add_nota_trabajo']);
    create([row()]);
    expect(component.canCreate).toBe(true);
    expect(component.canGenerateNota).toBe(true);
    expect(component.canEdit).toBe(false);
  });

  it('has no write permission without permissions', () => {
    create([row()]);
    expect(component.canCreate).toBe(false);
    expect(component.canEdit).toBe(false);
    expect(component.canGenerateNota).toBe(false);
  });

  it('shows the "assign a sucursal" state when the list is empty and the user has none', () => {
    const fixture = TestBed.createComponent(ProformasListComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    httpMock.expectOne(`${base}/proformas`).flush([]);
    httpMock.expectOne(`${base}/catalogo/sucursales`).flush([]);
    expect(component.withoutSucursal).toBe(true);
  });

  it('does not flag a missing sucursal when the user has one', () => {
    const fixture = TestBed.createComponent(ProformasListComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    httpMock.expectOne(`${base}/proformas`).flush([]);
    httpMock.expectOne(`${base}/catalogo/sucursales`).flush([{ id: 1, name: 'Central', address: 'x' }]);
    expect(component.withoutSucursal).toBe(false);
  });

  const tick = () => new Promise<void>((resolve) => setTimeout(resolve));

  it('generates the note after confirming and reloads the list', async () => {
    spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: true } as SweetAlertResult));
    create([row()]);

    const pending = component.generateNota(row());
    await tick();
    const req = httpMock.expectOne(`${base}/proformas/1/generar-nota-trabajo/`);
    expect(req.request.method).toBe('POST');
    req.flush({});
    httpMock.expectOne(`${base}/proformas`).flush([row({ is_close: true, status: 'nota_trabajo' })]);
    await pending;

    expect(component.rows[0].is_close).toBe(true);
  });

  it('does nothing when the confirmation is cancelled', async () => {
    spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: false } as SweetAlertResult));
    create([row()]);

    await component.generateNota(row());

    httpMock.expectNone(`${base}/proformas/1/generar-nota-trabajo/`);
  });

  it('shows the server message when generating the note fails', async () => {
    const fire = spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: true } as SweetAlertResult));
    create([row()]);

    const pending = component.generateNota(row());
    await tick();
    httpMock
      .expectOne(`${base}/proformas/1/generar-nota-trabajo/`)
      .flush({ detail: 'no hay lamina disponible' }, { status: 409, statusText: 'Conflict' });
    await pending;

    expect(fire).toHaveBeenCalledWith(
      jasmine.objectContaining({ title: 'No se pudo generar la nota de trabajo', text: 'no hay lamina disponible' })
    );
  });

  it('downloads the pdf of a proforma', () => {
    const createUrl = spyOn(URL, 'createObjectURL').and.returnValue('blob:pdf');
    spyOn(URL, 'revokeObjectURL');
    const click = spyOn(HTMLAnchorElement.prototype, 'click');
    create([row()]);

    component.downloadPdf(row());
    httpMock.expectOne(`${base}/proformas/1/pdf/`).flush(new Blob(['%PDF']));

    expect(createUrl).toHaveBeenCalled();
    expect(click).toHaveBeenCalled();
  });
});
