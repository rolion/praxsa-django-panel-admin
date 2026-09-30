import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/service/auth.service';
import { AppPrecioSucursal } from '../almacen.model';
import { PreciosSucursalListComponent } from './precios-sucursal-list.component';

const sample: AppPrecioSucursal[] = [
  { id: 1, sucursal: 1, sucursal_name: 'Central', lamina: 1, lamina_name: 'Carbon 20%', width: '1.50', precio_venta: '150.00' },
  { id: 2, sucursal: 2, sucursal_name: 'Norte', lamina: 2, lamina_name: 'Ceramico 30%', width: '1.80', precio_venta: '190.00' },
];

function loginAs(httpMock: HttpTestingController, authService: AuthService, groups: string[]): void {
  authService.login('user', 'pass').subscribe();
  httpMock
    .expectOne(`${environment.apiUrl}/product/api-panel-admin-token-auth/`)
    .flush({ token: 't', user_id: 1, username: 'user', name: 'U', lastname: 'U', is_staff: true, groups });
}

describe('PreciosSucursalListComponent', () => {
  let component: PreciosSucursalListComponent;
  let httpMock: HttpTestingController;
  let authService: AuthService;
  const base = `${environment.apiUrl}/product/almacen/precios-sucursal`;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [PreciosSucursalListComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), NgbModal],
    });
    httpMock = TestBed.inject(HttpTestingController);
    authService = TestBed.inject(AuthService);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  function createComponent() {
    const fixture = TestBed.createComponent(PreciosSucursalListComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    httpMock.expectOne((r) => r.url === base).flush(sample);
    return fixture;
  }

  it('loads precios into rows', () => {
    createComponent();

    expect(component.rows).toEqual(sample);
  });

  it('filterDatatable() matches by lamina or sucursal name', () => {
    createComponent();

    component.filterDatatable({ target: { value: 'ceramico' } } as unknown as Event);
    expect(component.rows.map((r) => r.id)).toEqual([2]);

    component.filterDatatable({ target: { value: 'central' } } as unknown as Event);
    expect(component.rows.map((r) => r.id)).toEqual([1]);
  });

  it('canManage is false for a non-admin group and true for admin', () => {
    loginAs(httpMock, authService, ['almacen']);
    createComponent();
    expect(component.canManage).toBe(false);

    loginAs(httpMock, authService, ['admin']);
    expect(component.canManage).toBe(true);
  });

  it('save() does not call the API when width or price are not positive', () => {
    createComponent();
    component.form.setValue({ sucursal: 1, lamina: 1, width: '0', precio_venta: '-3' });

    component.save();

    expect(component.form.invalid).toBe(true);
    httpMock.expectNone(base);
  });

  it('save() POSTs a new precio and reloads the list', () => {
    createComponent();
    component.editingId = null;
    component.form.setValue({ sucursal: 1, lamina: 2, width: '1.20', precio_venta: '160.00' });

    component.save();

    const req = httpMock.expectOne((r) => r.url === base && r.method === 'POST');
    expect(req.request.body).toEqual({ sucursal: 1, lamina: 2, width: '1.20', precio_venta: '160.00' });
    req.flush({ ...sample[0], id: 3 });
    httpMock.expectOne((r) => r.url === base && r.method === 'GET').flush(sample);
  });

  it('save() PATCHes when editing and surfaces the duplicate error', () => {
    createComponent();
    component.editingId = 1;
    component.form.setValue({ sucursal: 1, lamina: 1, width: '1.50', precio_venta: '150.00' });

    component.save();

    const req = httpMock.expectOne(`${base}/1/`);
    expect(req.request.method).toBe('PATCH');
    req.flush(
      { non_field_errors: ['Ya existe un precio para la lámina Carbon 20%.'] },
      { status: 400, statusText: 'Bad Request' }
    );
    expect(component.formError).toContain('Ya existe un precio');
    expect(component.saving).toBe(false);
  });
});
