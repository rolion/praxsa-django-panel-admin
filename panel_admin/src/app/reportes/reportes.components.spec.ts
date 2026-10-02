import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { environment } from '../../environments/environment';
import { AuthService } from '../core/service/auth.service';
import { hoyIso, inicioMesIso } from './reportes.filtros';
import { ResumenUtilidad, ResumenVentas, UtilidadReport, VentasDiariasReport } from './reportes.model';
import { UtilidadComponent } from './utilidad/utilidad.component';
import { VentasDiariasComponent } from './ventas-diarias/ventas-diarias.component';

const api = `${environment.apiUrl}/product`;

const resumen = (overrides: Partial<ResumenVentas> = {}): ResumenVentas => ({
  ventas: 2, venta_lamina: '780.00', instalacion: '100.00', bruto: '880.00', descuento: '0.00', cobrado: '880.00', ...overrides,
});

const ventasReport = (overrides: Partial<VentasDiariasReport> = {}): VentasDiariasReport => ({
  rows: [{
    nota_venta_id: 7, nota_trabajo_id: 3, proforma_id: 5, fecha: '2026-09-30T10:15:00', cliente: 'Ana',
    sales_type: 'venta_instalacion', sales_type_label: 'Venta con Instalación', sucursal_id: 1, sucursal_name: 'Central',
    venta_lamina: '480.00', instalacion: '100.00', bruto: '580.00', descuento: '30.00', cobrado: '550.00',
    pago_id: 9, vehiculo: 'Corolla', tipo_pago: 'efec', tipo_pago_label: 'Efectivo', registro_contable: '1234/26', cerrado: false,
  }],
  totales: resumen(),
  por_tipo_venta: [
    { sales_type: 'venta_instalacion', label: 'Venta con Instalación', ...resumen({ ventas: 1 }) },
    { sales_type: 'venta_metro_lineal', label: 'Venta Metro Lineal', ...resumen({ ventas: 1 }) },
  ],
  por_tipo_pago: [
    { tipo_pago: 'efec', label: 'Efectivo', ...resumen({ ventas: 1 }) },
    { tipo_pago: 'trans', label: 'Targeta/QR', ...resumen({ ventas: 1 }) },
  ],
  sin_sucursal: false,
  ...overrides,
});

const resumenUtilidad = (overrides: Partial<ResumenUtilidad> = {}): ResumenUtilidad => ({
  ...resumen(), costo_compra: '560.00', utilidad_antes: '220.00', utilidad_despues: '190.00', margen: '21.59',
  ventas_costo_incompleto: 0, ...overrides,
});

const utilidadReport = (overrides: Partial<UtilidadReport> = {}): UtilidadReport => ({
  ventas: [{
    nota_venta_id: 7, nota_trabajo_id: 3, proforma_id: 5, fecha: '2026-09-30T10:15:00', cliente: 'Ana',
    sales_type: 'venta_instalacion', sales_type_label: 'Venta con Instalación', sucursal_id: 1, sucursal_name: 'Central',
    venta_lamina: '480.00', instalacion: '100.00', bruto: '580.00', descuento: '30.00', cobrado: '550.00',
    costo_compra: '320.00', utilidad_antes: '160.00', utilidad_despues: '130.00', margen: '23.64', costo_incompleto: false,
  }],
  por_lamina: [{
    sucursal_id: 1, sucursal_name: 'Central', window_film_id: 2, window_film_name: 'Ceramica', width: '1.50',
    metros: '4.00', venta_lamina: '480.00', costo_compra: '320.00', utilidad_antes: '160.00',
  }],
  totales: resumenUtilidad(),
  por_tipo_venta: [{ sales_type: 'venta_instalacion', label: 'Venta con Instalación', ...resumenUtilidad() }],
  sin_sucursal: false,
  ...overrides,
});

describe('Pantallas de reportes', () => {
  let httpMock: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  function login(permissions: string[]): void {
    TestBed.inject(AuthService).login('u', 'p').subscribe();
    httpMock.expectOne(`${api}/api-panel-admin-token-auth/`).flush({
      token: 't', user_id: 1, username: 'u', name: 'U', lastname: 'U', is_staff: true, groups: [], permissions,
    });
  }

  const sucursales = (n = 1) => Array.from({ length: n }, (_, i) => ({ id: i + 1, name: `Sucursal ${i + 1}`, address: '' }));
  const conInactiva = [
    { id: 1, name: 'Central', address: '', activa: true },
    { id: 2, name: 'Norte', address: '', activa: false },
  ];

  function text(fixture: ComponentFixture<unknown>): string {
    return (fixture.nativeElement as HTMLElement).textContent ?? '';
  }

  describe('VentasDiariasComponent', () => {
    function create(perms: string[] = ['product.view_proxy_pagos']) {
      login(perms);
      const fixture = TestBed.createComponent(VentasDiariasComponent);
      fixture.detectChanges();
      return fixture;
    }

    function flushInicial(
      report: VentasDiariasReport, nSucursales = 1, catalogo: object[] = sucursales(nSucursales),
    ) {
      httpMock.expectOne(`${api}/ordenes/catalogo/sucursales`).flush(catalogo);
      const req = httpMock.expectOne((r) => r.url === `${api}/reportes/ventas-diarias`);
      req.flush(report);
      return req;
    }

    it('por defecto consulta el dia de hoy y muestra totales y desgloses', () => {
      const fixture = create();
      const req = flushInicial(ventasReport());
      expect(req.request.params.get('desde')).toBe(hoyIso());
      expect(req.request.params.get('hasta')).toBe(hoyIso());
      fixture.detectChanges();
      const contenido = text(fixture);
      expect(contenido).toContain('880.00 Bs');
      expect(contenido).toContain('Venta Metro Lineal');
      expect(contenido).toContain('Targeta/QR');
    });

    it('sin el permiso no consulta la API y avisa', () => {
      const fixture = create([]);
      httpMock.expectNone(`${api}/reportes/ventas-diarias`);
      fixture.detectChanges();
      expect(text(fixture)).toContain('No tiene permiso para ver este reporte.');
    });

    it('con una sola sucursal la muestra fija, sin selector', () => {
      const fixture = create();
      flushInicial(ventasReport(), 1);
      fixture.detectChanges();
      expect((fixture.nativeElement as HTMLElement).querySelector('#rv-sucursal')).toBeNull();
      expect(text(fixture)).toContain('Sucursal 1');
    });

    it('con varias sucursales ofrece el selector', () => {
      const fixture = create();
      flushInicial(ventasReport(), 2);
      fixture.detectChanges();
      expect((fixture.nativeElement as HTMLElement).querySelector('#rv-sucursal')).not.toBeNull();
    });

    it('por defecto marca solo las sucursales activas', () => {
      const fixture = create();
      flushInicial(ventasReport(), 0, [...conInactiva, { id: 3, name: 'Sur', address: '', activa: true }]);

      expect(fixture.componentInstance.filtros.controls.sucursales.value).toEqual([1, 3]);
    });

    it('con una sucursal inactiva muestra el multiselect para poder marcarla', () => {
      const fixture = create();
      flushInicial(ventasReport(), 0, conInactiva);
      fixture.detectChanges();

      expect((fixture.nativeElement as HTMLElement).querySelector('#rv-sucursal')).not.toBeNull();
      expect(text(fixture)).toContain('Todas las activas');
    });

    it('con todas las sucursales inactivas las marca y vuelve a consultar', () => {
      const fixture = create();
      httpMock.expectOne(`${api}/ordenes/catalogo/sucursales`).flush([conInactiva[1]]);

      expect(fixture.componentInstance.filtros.controls.sucursales.value).toEqual([2]);
      const peticiones = httpMock.match((r) => r.url === `${api}/reportes/ventas-diarias`);
      expect(peticiones.length).toBe(2); // la inicial (por defecto) y el reintento con la inactiva marcada
      expect(peticiones[0].request.params.has('sucursales')).toBeFalse();
      expect(peticiones[1].request.params.get('sucursales')).toBe('2');
      peticiones.forEach((peticion) => peticion.flush(ventasReport()));
    });

    it('marcar una inactiva envia la lista explicita de sucursales', () => {
      const fixture = create();
      flushInicial(ventasReport(), 0, conInactiva);
      const control = fixture.componentInstance.filtros.controls.sucursales;

      control.setValue([1, 2]);
      fixture.componentInstance.aplicar();

      const req = httpMock.expectOne((r) => r.url === `${api}/reportes/ventas-diarias`);
      expect(req.request.params.get('sucursales')).toBe('1,2');
      req.flush(ventasReport());
    });

    it('un rango invalido muestra el error y no consulta', () => {
      const fixture = create();
      flushInicial(ventasReport());
      const component = fixture.componentInstance;
      component.filtros.patchValue({ desde: '2026-09-30', hasta: '2026-09-01' });
      component.aplicar();
      httpMock.expectNone((r) => r.url === `${api}/reportes/ventas-diarias`);
      fixture.detectChanges();
      expect(text(fixture)).toContain('La fecha inicial no puede ser mayor que la final.');
    });

    it('Aplicar envia los filtros elegidos y Limpiar vuelve a los valores por defecto', () => {
      const fixture = create();
      flushInicial(ventasReport());
      const component = fixture.componentInstance;
      component.filtros.patchValue({ desde: '2026-09-01', salesType: 'venta_metro_lineal', tipoPago: 'trans', sucursales: [1] });
      component.aplicar();
      const req = httpMock.expectOne((r) => r.url === `${api}/reportes/ventas-diarias`);
      expect(req.request.params.get('sales_type')).toBe('venta_metro_lineal');
      expect(req.request.params.get('tipo_pago')).toBe('trans');
      expect(req.request.params.get('sucursales')).toBe('1');
      req.flush(ventasReport());

      component.limpiar();
      const limpio = httpMock.expectOne((r) => r.url === `${api}/reportes/ventas-diarias`);
      expect(limpio.request.params.get('desde')).toBe(hoyIso());
      expect(limpio.request.params.has('sales_type')).toBeFalse();
      limpio.flush(ventasReport());
    });

    it('muestra el aviso de sin sucursal', () => {
      const fixture = create();
      flushInicial(ventasReport({ rows: [], sin_sucursal: true }));
      fixture.detectChanges();
      expect(text(fixture)).toContain('Asigne una sucursal al usuario');
    });

    it('muestra el aviso de periodo sin ventas', () => {
      const fixture = create();
      flushInicial(ventasReport({ rows: [] }));
      fixture.detectChanges();
      expect(text(fixture)).toContain('No hay ventas pagadas en el período seleccionado.');
    });

    it('muestra el mensaje del servidor si la consulta falla', () => {
      const fixture = create();
      httpMock.expectOne(`${api}/ordenes/catalogo/sucursales`).flush(sucursales());
      httpMock
        .expectOne((r) => r.url === `${api}/reportes/ventas-diarias`)
        .flush({ detail: 'No tiene permiso para realizar esta acción.' }, { status: 403, statusText: 'Forbidden' });
      fixture.detectChanges();
      expect(text(fixture)).toContain('No tiene permiso para realizar esta acción.');
    });

    it('la busqueda client-side filtra por cliente', () => {
      const fixture = create();
      flushInicial(ventasReport());
      const component = fixture.componentInstance;
      component.filterDatatable({ target: { value: 'zzz' } } as unknown as Event);
      expect(component.rows.length).toBe(0);
      component.filterDatatable({ target: { value: 'ana' } } as unknown as Event);
      expect(component.rows.length).toBe(1);
    });
  });

  describe('UtilidadComponent', () => {
    function create(perms: string[] = ['product.view_utilidades']) {
      login(perms);
      const fixture = TestBed.createComponent(UtilidadComponent);
      fixture.detectChanges();
      return fixture;
    }

    function flushInicial(report: UtilidadReport) {
      httpMock.expectOne(`${api}/ordenes/catalogo/sucursales`).flush(sucursales());
      const req = httpMock.expectOne((r) => r.url === `${api}/reportes/utilidad`);
      req.flush(report);
      return req;
    }

    it('por defecto consulta el mes en curso y muestra utilidad con y sin descuento', () => {
      const fixture = create();
      const req = flushInicial(utilidadReport());
      expect(req.request.params.get('desde')).toBe(inicioMesIso());
      expect(req.request.params.get('hasta')).toBe(hoyIso());
      expect(req.request.params.has('tipo_pago')).toBeFalse();
      fixture.detectChanges();
      const contenido = text(fixture);
      expect(contenido).toContain('Utilidad antes de descuento');
      expect(contenido).toContain('220.00 Bs');
      expect(contenido).toContain('190.00 Bs');
      expect(contenido).toContain('21.59 %');
      expect(contenido).toContain('Ingreso por instalación (aparte)');
      expect(contenido).toContain('Ceramica');
    });

    it('sin el permiso no consulta la API y avisa (Caja no ve Utilidad)', () => {
      const fixture = create(['product.view_proxy_pagos']);
      httpMock.expectNone(`${api}/reportes/utilidad`);
      fixture.detectChanges();
      expect(text(fixture)).toContain('No tiene permiso para ver este reporte.');
    });

    it('avisa cuando hay ventas con costo de compra incompleto', () => {
      const fixture = create();
      flushInicial(utilidadReport({ totales: resumenUtilidad({ ventas_costo_incompleto: 3 }) }));
      fixture.detectChanges();
      expect(text(fixture)).toContain('Ventas con costo de compra incompleto: 3; su utilidad está sobreestimada.');
    });

    it('no muestra el aviso cuando todas las ventas tienen costo', () => {
      const fixture = create();
      flushInicial(utilidadReport());
      fixture.detectChanges();
      expect(text(fixture)).not.toContain('costo de compra incompleto');
    });

    it('marca la fila de la venta con costo incompleto', () => {
      const fixture = create();
      const base = utilidadReport();
      flushInicial({ ...base, ventas: [{ ...base.ventas[0], costo_incompleto: true }] });
      fixture.detectChanges();
      expect((fixture.nativeElement as HTMLElement).querySelector('.reporte-warn')).not.toBeNull();
    });

    it('un rango de mas de 366 dias no consulta', () => {
      const fixture = create();
      flushInicial(utilidadReport());
      fixture.componentInstance.filtros.patchValue({ desde: '2025-01-01', hasta: '2026-09-30' });
      fixture.componentInstance.aplicar();
      httpMock.expectNone((r) => r.url === `${api}/reportes/utilidad`);
      expect(fixture.componentInstance.rangeError).toContain('366');
    });
  });
});
