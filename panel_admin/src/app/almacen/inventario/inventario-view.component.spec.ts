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

  function render(inv: Partial<AppInventario> = {}): HTMLElement {
    const fixture = TestBed.createComponent(InventarioViewComponent);
    fixture.detectChanges();
    httpMock.expectOne(`${base}/7/`).flush({ ...sampleInventario, ...inv });
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  const text = (el: HTMLElement, key: string) =>
    el.querySelector(`[data-test="${key}"]`)?.textContent?.replace(/\s+/g, ' ').trim();

  it('muestra titulo, nombre del producto y datos de Informacion General', () => {
    const el = render({ date: '2026-09-27T14:30:00', nro_lote: 'L1', numero_referencia: 12 });
    expect(text(el, 'title')).toBe('Detalle de Registro');
    expect(el.querySelector('[data-test="title"]')?.classList).toContain('inventario-title');
    expect(text(el, 'product-name')).toBe('Carbon 20%');
    expect(text(el, 'sucursal')).toBe('Central');
    expect(text(el, 'lamina')).toBe('Carbon 20%');
    expect(text(el, 'ancho')).toContain('1,5');
    expect(text(el, 'lote')).toBe('L1');
    expect(text(el, 'referencia')).toBe('12');
    expect(text(el, 'fecha')).toBe('27/09/2026 - 14:30 h');
  });

  it('la fecha de registro aparece despues del estado', () => {
    const el = render();
    const status = el.querySelector('[data-test="status"]') as Node;
    const fecha = el.querySelector('[data-test="fecha"]') as Node;
    expect(status.compareDocumentPosition(fecha) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('el estado activo es un badge verde', () => {
    const el = render({ is_active: true });
    expect(el.querySelector('[data-test="status"]')?.classList).toContain('bg-success');
    expect(text(el, 'status')).toBe('Activo');
  });

  it('el estado inactivo es un badge gris', () => {
    const el = render({ is_active: false });
    expect(el.querySelector('[data-test="status"]')?.classList).toContain('bg-secondary');
    expect(text(el, 'status')).toBe('Inactivo');
  });

  it('muestra un guion si no hay numero de lote', () => {
    const el = render({ nro_lote: null });
    expect(text(el, 'lote')).toBe('—');
  });

  it('muestra metricas de stock y valores financieros', () => {
    const el = render({
      to_install: '40.50', installed: '9.50', original_length: '50.00', quantity: 3,
      precio_compra_mtr_lineal: '80.00', precio_venta_mtr_lineal: '120.50',
    });
    expect(text(el, 'disponible')).toContain('40,5');
    expect(text(el, 'instalado')).toContain('9,5');
    expect(text(el, 'longitud-inicial')).toContain('50');
    expect(text(el, 'cantidad')).toBe('3');
    expect(text(el, 'precio-compra')).toBe('Bs 80');
    expect(text(el, 'precio-venta')).toBe('Bs 120,5');
  });

  it('formatMeters usa el formato es-BO con hasta 2 decimales', () => {
    const component = TestBed.createComponent(InventarioViewComponent).componentInstance;
    const expected = new Intl.NumberFormat('es-BO', { maximumFractionDigits: 2 });
    expect(component.formatMeters('50.00')).toBe(expected.format(50));
    expect(component.formatMeters('1234.5')).toBe(expected.format(1234.5));
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

  it('muestra solo el boton Editar con change_inventario', () => {
    localStorage.clear();
    loginWith(['product.change_inventario']);
    const el = render();
    const edit = el.querySelector('[data-test="edit-button"]');
    expect(edit?.textContent?.trim()).toBe('Editar');
    expect(edit?.getAttribute('href')).toBe('/almacen/inventario/edit/7');
    expect(el.querySelectorAll('.btn').length).toBe(1);
    expect(el.textContent).not.toContain('Gestionar');
    localStorage.clear();
  });

  it('oculta el boton Editar sin change_inventario', () => {
    localStorage.clear();
    loginWith(['product.view_inventario']);
    const el = render();
    expect(el.querySelector('[data-test="edit-button"]')).toBeNull();
    expect(el.querySelectorAll('.btn').length).toBe(0);
    localStorage.clear();
  });
});
