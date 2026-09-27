import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/service/auth.service';
import { AppInventario } from '../almacen.model';
import { InventarioListComponent } from './inventario-list.component';

const sampleRows: AppInventario[] = [
  {
    id: 1, sucursal: 1, sucursal_name: 'Central', bobina: 1, window_film_name: 'Carbon 20%',
    bobina_width: '1.50', quantity: 1, to_install: '50.00', installed: '0.00',
    original_length: '50.00', date: '2026-09-01T00:00:00Z', numero_referencia: 1,
    precio_compra_mtr_lineal: '80.00', precio_venta_mtr_lineal: '120.00', nro_lote: 'L1',
    is_active: true,
  },
];

function loginAs(httpMock: HttpTestingController, authService: AuthService, groups: string[]): void {
  authService.login('user', 'pass').subscribe();
  httpMock
    .expectOne(`${environment.apiUrl}/product/api-panel-admin-token-auth/`)
    .flush({ token: 't', user_id: 1, username: 'user', name: 'U', lastname: 'U', is_staff: true, groups });
}

describe('InventarioListComponent', () => {
  let component: InventarioListComponent;
  let httpMock: HttpTestingController;
  let authService: AuthService;
  const base = `${environment.apiUrl}/product/almacen/inventario`;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [InventarioListComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    httpMock = TestBed.inject(HttpTestingController);
    authService = TestBed.inject(AuthService);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  function createComponent() {
    const fixture = TestBed.createComponent(InventarioListComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    return fixture;
  }

  it('loads inventario rows from the API', () => {
    createComponent();
    httpMock.expectOne((r) => r.url === base).flush(sampleRows);

    expect(component.rows).toEqual(sampleRows);
  });

  it('filterDatatable() matches by lote', () => {
    createComponent();
    httpMock.expectOne((r) => r.url === base).flush(sampleRows);

    component.filterDatatable({ target: { value: 'l1' } } as unknown as Event);

    expect(component.rows.length).toBe(1);

    component.filterDatatable({ target: { value: 'no-existe' } } as unknown as Event);
    expect(component.rows.length).toBe(0);
  });

  it('canManage is false for the almacen group', () => {
    loginAs(httpMock, authService, ['almacen']);
    createComponent();
    httpMock.expectOne((r) => r.url === base).flush(sampleRows);

    expect(component.canManage).toBe(false);
  });

  it('canManage is true for the admin group', () => {
    loginAs(httpMock, authService, ['admin']);
    createComponent();
    httpMock.expectOne((r) => r.url === base).flush(sampleRows);

    expect(component.canManage).toBe(true);
  });
});
