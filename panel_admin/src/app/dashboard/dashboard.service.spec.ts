import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../environments/environment';
import { DashboardService } from './dashboard.service';

describe('DashboardService', () => {
  let service: DashboardService;
  let httpMock: HttpTestingController;
  const base = `${environment.apiUrl}/product/dashboard`;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(DashboardService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function params(url: string, call: () => void): Record<string, string | null> {
    call();
    const req = httpMock.expectOne((r) => r.url === `${base}/${url}`);
    expect(req.request.method).toBe('GET');
    const out: Record<string, string | null> = {};
    req.request.params.keys().forEach((k) => (out[k] = req.request.params.get(k)));
    req.flush({});
    return out;
  }

  it('does not send empty parameters', () => {
    expect(params('kpis', () => service.getKpis().subscribe())).toEqual({});
    expect(params('kpis', () => service.getKpis({ sucursal: null }).subscribe())).toEqual({});
  });

  it('sends only the sucursal to the endpoints that do not take a period', () => {
    const all = { sucursal: 3, meses: 6, todos: true };
    expect(params('kpis', () => service.getKpis(all).subscribe())).toEqual({ sucursal: '3' });
    expect(params('cola-taller', () => service.getColaTaller(all).subscribe())).toEqual({ sucursal: '3' });
    expect(params('proformas-recientes', () => service.getProformasRecientes(all).subscribe())).toEqual({ sucursal: '3' });
  });

  it('sends the period to the historical widgets', () => {
    const all = { sucursal: 3, meses: 6, todos: true };
    expect(params('proformas-vs-ventas', () => service.getProformasVsVentas(all).subscribe())).toEqual({ sucursal: '3', meses: '6' });
    expect(params('consumo-laminas', () => service.getConsumoLaminas(all).subscribe())).toEqual({ sucursal: '3', meses: '6' });
    expect(params('items-solicitados', () => service.getItemsSolicitados(all).subscribe())).toEqual({ sucursal: '3', meses: '6' });
  });

  it('sends "todos" only to the stock widget and only when it is on', () => {
    expect(params('stock-critico', () => service.getStockCritico({ todos: true }).subscribe())).toEqual({ todos: 'true' });
    expect(params('stock-critico', () => service.getStockCritico({ todos: false }).subscribe())).toEqual({});
  });
});
