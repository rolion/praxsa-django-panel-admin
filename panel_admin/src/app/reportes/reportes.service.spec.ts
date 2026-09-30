import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../environments/environment';
import { bs, fechaHora, hoyIso, inicioMesIso, porcentaje, rangoInvalido, toIso } from './reportes.filtros';
import { ReportesService } from './reportes.service';

const base = `${environment.apiUrl}/product/reportes`;

describe('ReportesService', () => {
  let service: ReportesService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(ReportesService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('ventas diarias envia solo los filtros con valor', () => {
    service.getVentasDiarias({ desde: '2026-09-01', hasta: '2026-09-30' }).subscribe();
    const req = httpMock.expectOne((r) => r.url === `${base}/ventas-diarias`);
    expect(req.request.method).toBe('GET');
    expect(req.request.params.keys().sort()).toEqual(['desde', 'hasta']);
    req.flush({});
  });

  it('ventas diarias envia sucursal, tipo de venta y tipo de pago', () => {
    service
      .getVentasDiarias({ desde: '2026-09-01', hasta: '2026-09-30', sucursal: 4, salesType: 'venta_metro_lineal', tipoPago: 'trans' })
      .subscribe();
    const req = httpMock.expectOne((r) => r.url === `${base}/ventas-diarias`);
    expect(req.request.params.get('sucursal')).toBe('4');
    expect(req.request.params.get('sales_type')).toBe('venta_metro_lineal');
    expect(req.request.params.get('tipo_pago')).toBe('trans');
    req.flush({});
  });

  it('utilidad no envia el tipo de pago', () => {
    service
      .getUtilidad({ desde: '2026-09-01', hasta: '2026-09-30', salesType: 'venta_instalacion', tipoPago: 'efec' })
      .subscribe();
    const req = httpMock.expectOne((r) => r.url === `${base}/utilidad`);
    expect(req.request.params.get('sales_type')).toBe('venta_instalacion');
    expect(req.request.params.has('tipo_pago')).toBeFalse();
    req.flush({});
  });
});

describe('reportes.filtros', () => {
  it('toIso, hoyIso e inicioMesIso usan la fecha local', () => {
    const now = new Date(2026, 8, 30, 23, 59); // 30 de septiembre de 2026
    expect(toIso(now)).toBe('2026-09-30');
    expect(hoyIso(now)).toBe('2026-09-30');
    expect(inicioMesIso(now)).toBe('2026-09-01');
  });

  it('rangoInvalido replica las reglas del servidor', () => {
    expect(rangoInvalido('2026-09-01', '2026-09-30')).toBe('');
    expect(rangoInvalido('2026-09-01', '2026-09-01')).toBe('');
    expect(rangoInvalido('', '2026-09-30')).toContain('fecha inicial');
    expect(rangoInvalido('2026-09-30', '2026-09-01')).toBe('La fecha inicial no puede ser mayor que la final.');
    expect(rangoInvalido('2024-01-01', '2024-12-31')).toBe(''); // 366 dias (bisiesto)
    expect(rangoInvalido('2025-01-01', '2026-01-02')).toContain('366');
  });

  it('formatea fechas', () => {
    expect(fechaHora('2026-09-30T10:15:00')).toBe('30/09/2026 10:15');
    expect(fechaHora('2026-09-30')).toBe('30/09/2026');
    expect(fechaHora(null)).toBe('');
  });

  it('formatea importes y porcentajes', () => {
    expect(bs('340.00')).toBe('340.00 Bs');
    expect(bs(null)).toBe('0.00 Bs');
    expect(porcentaje('23.64')).toBe('23.64 %');
    expect(porcentaje(null)).toBe('—');
  });
});
