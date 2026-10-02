import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/service/auth.service';
import { AppInventario, AppSucursal, AppWindowFilm } from '../almacen.model';
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

const oneSucursal: AppSucursal[] = [{ id: 1, name: 'Central' }];
const twoSucursales: AppSucursal[] = [
  { id: 1, name: 'Central' },
  { id: 2, name: 'Norte' },
];
const sampleLaminas: AppWindowFilm[] = [
  { id: 5, name: 'Carbon 20%', description: '', content: null, image: null, is_active: true },
];

function loginAs(
  httpMock: HttpTestingController,
  authService: AuthService,
  groups: string[],
  permissions: string[] = []
): void {
  authService.login('user', 'pass').subscribe();
  httpMock
    .expectOne(`${environment.apiUrl}/product/api-panel-admin-token-auth/`)
    .flush({
      token: 't', user_id: 1, username: 'user', name: 'U', lastname: 'U', is_staff: true, groups, permissions,
    });
}

describe('InventarioListComponent', () => {
  let component: InventarioListComponent;
  let httpMock: HttpTestingController;
  let authService: AuthService;
  const almacen = `${environment.apiUrl}/product/almacen`;
  const base = `${almacen}/inventario`;

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

  /** Crea el componente y responde laminas, sucursales en alcance y el primer listado. */
  function createComponent(sucursales: AppSucursal[] = oneSucursal) {
    const fixture = TestBed.createComponent(InventarioListComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    httpMock.expectOne((r) => r.url === `${almacen}/laminas`).flush(sampleLaminas);
    httpMock.expectOne(`${almacen}/sucursales`).flush(sucursales);
    httpMock.expectOne((r) => r.url === base).flush(sampleRows);
    return fixture;
  }

  it('loads inventario rows from the API', () => {
    createComponent();

    expect(component.rows).toEqual(sampleRows);
  });

  it('con una sola sucursal la preselecciona, la bloquea y la pide al servidor', () => {
    const fixture = TestBed.createComponent(InventarioListComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    httpMock.expectOne((r) => r.url === `${almacen}/laminas`).flush(sampleLaminas);
    httpMock.expectOne(`${almacen}/sucursales`).flush(oneSucursal);
    const req = httpMock.expectOne((r) => r.url === base);
    expect(req.request.params.get('sucursal')).toBe('1');
    req.flush(sampleRows);

    expect(component.sucursalLocked).toBe(true);
    expect(component.selectedSucursal).toBe(1);
  });

  it('con varias sucursales no preselecciona ninguna y ofrece "Todas mis sucursales"', () => {
    const fixture = TestBed.createComponent(InventarioListComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    httpMock.expectOne((r) => r.url === `${almacen}/laminas`).flush(sampleLaminas);
    httpMock.expectOne(`${almacen}/sucursales`).flush(twoSucursales);
    const req = httpMock.expectOne((r) => r.url === base);
    expect(req.request.params.has('sucursal')).toBe(false);
    req.flush(sampleRows);

    expect(component.sucursalLocked).toBe(false);
    expect(component.selectedSucursal).toBeNull();
    expect(component.sucursalPlaceholder).toBe('Todas mis sucursales');
  });

  it('un admin ve "Todas las sucursales"', () => {
    loginAs(httpMock, authService, ['admin']);
    createComponent(twoSucursales);

    expect(component.sucursalPlaceholder).toBe('Todas las sucursales');
  });

  it('sin sucursales en alcance muestra el aviso y oculta el alta', () => {
    loginAs(httpMock, authService, ['almacen'], ['product.add_inventario']);
    createComponent([]);

    expect(component.withoutSucursales).toBe(true);
    expect(component.canCreate).toBe(false);
  });

  it('cambiar el filtro de sucursal recarga el listado con ?sucursal=', () => {
    createComponent(twoSucursales);

    component.onSucursalChange({ target: { value: '2' } } as unknown as Event);

    const req = httpMock.expectOne((r) => r.url === base);
    expect(req.request.params.get('sucursal')).toBe('2');
    req.flush(sampleRows);
    expect(component.selectedSucursal).toBe(2);
  });

  it('cambiar el filtro de lamina recarga con ?window_film= y combina con la sucursal', () => {
    createComponent();

    component.onLaminaChange({ target: { value: '5' } } as unknown as Event);

    const req = httpMock.expectOne((r) => r.url === base);
    expect(req.request.params.get('window_film')).toBe('5');
    expect(req.request.params.get('sucursal')).toBe('1');
    req.flush(sampleRows);
  });

  it('elegir "todas" (valor vacio) quita el filtro', () => {
    createComponent(twoSucursales);
    component.onSucursalChange({ target: { value: '2' } } as unknown as Event);
    httpMock.expectOne((r) => r.url === base).flush(sampleRows);

    component.onSucursalChange({ target: { value: '' } } as unknown as Event);

    const req = httpMock.expectOne((r) => r.url === base);
    expect(req.request.params.has('sucursal')).toBe(false);
    req.flush(sampleRows);
    expect(component.selectedSucursal).toBeNull();
  });

  it('filterDatatable() matches by lote', () => {
    createComponent();

    component.filterDatatable({ target: { value: 'l1' } } as unknown as Event);

    expect(component.rows.length).toBe(1);

    component.filterDatatable({ target: { value: 'no-existe' } } as unknown as Event);
    expect(component.rows.length).toBe(0);
  });

  it('canCreate y canEdit dependen de los permisos, no del grupo', () => {
    loginAs(httpMock, authService, ['almacen'], ['product.add_inventario', 'product.change_inventario']);
    createComponent();

    expect(component.canCreate).toBe(true);
    expect(component.canEdit).toBe(true);
  });

  it('sin permisos de escritura no se puede crear ni editar, aunque sea del grupo admin', () => {
    loginAs(httpMock, authService, ['admin'], ['product.view_inventario']);
    createComponent();

    expect(component.canCreate).toBe(false);
    expect(component.canEdit).toBe(false);
  });

  it('puede crear sin poder editar si solo tiene add_inventario', () => {
    loginAs(httpMock, authService, ['almacen'], ['product.add_inventario']);
    createComponent();

    expect(component.canCreate).toBe(true);
    expect(component.canEdit).toBe(false);
  });
});
