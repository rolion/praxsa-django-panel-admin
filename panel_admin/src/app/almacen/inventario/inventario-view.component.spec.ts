import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/service/auth.service';
import { AppInventario } from '../almacen.model';
import { InventarioViewComponent } from './inventario-view.component';

const sampleInventario: AppInventario = {
  id: 7, sucursal: 1, sucursal_name: 'Central', sucursal_activa: true, bobina: 1, window_film_name: 'Carbon 20%',
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

  function loginWith(permissions: string[]): void {
    TestBed.inject(AuthService).login('user', 'pass').subscribe();
    httpMock
      .expectOne(`${environment.apiUrl}/product/api-panel-admin-token-auth/`)
      .flush({
        token: 't', user_id: 1, username: 'user', name: 'U', lastname: 'U', is_staff: true,
        groups: ['almacen'], permissions,
      });
  }

  it('una sucursal inactiva se ve pero no se puede gestionar', () => {
    localStorage.clear();
    loginWith(['product.change_inventario']);
    const fixture = TestBed.createComponent(InventarioViewComponent);
    fixture.detectChanges();
    httpMock.expectOne(`${base}/7/`).flush({ ...sampleInventario, sucursal_activa: false });
    fixture.detectChanges();

    expect(fixture.componentInstance.sucursalInactiva).toBe(true);
    expect(fixture.componentInstance.canManage).toBe(false);
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('solo lectura');
    localStorage.clear();
  });

  it('canManage depende del permiso change_inventario, no del grupo', () => {
    localStorage.clear();
    loginWith(['product.change_inventario']);
    const fixture = TestBed.createComponent(InventarioViewComponent);
    expect(fixture.componentInstance.canManage).toBe(true);

    localStorage.clear();
    loginWith(['product.view_inventario']);
    expect(fixture.componentInstance.canManage).toBe(false);
    localStorage.clear();
  });
});
