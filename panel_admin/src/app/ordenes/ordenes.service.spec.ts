import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../environments/environment';
import { previewSubtotal } from './ordenes.calc';
import { extractApiError } from './ordenes.errors';
import { OrdenesService } from './ordenes.service';

describe('OrdenesService', () => {
  let service: OrdenesService;
  let httpMock: HttpTestingController;
  const base = `${environment.apiUrl}/product/ordenes`;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(OrdenesService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('lists proformas with optional filters', () => {
    service.listProformas({ search: 'abc', salesType: 'venta_metro_lineal', status: 'proforma' }).subscribe();
    const req = httpMock.expectOne((r) => r.url === `${base}/proformas`);
    expect(req.request.params.get('search')).toBe('abc');
    expect(req.request.params.get('sales_type')).toBe('venta_metro_lineal');
    expect(req.request.params.get('status')).toBe('proforma');
    req.flush([]);
  });

  it('creates and patches proformas', () => {
    service.createProforma({} as never).subscribe();
    const post = httpMock.expectOne(`${base}/proformas`);
    expect(post.request.method).toBe('POST');
    post.flush({});

    service.updateProforma(5, { name: 'x' }).subscribe();
    const patch = httpMock.expectOne(`${base}/proformas/5/`);
    expect(patch.request.method).toBe('PATCH');
    patch.flush({});
  });

  it('generates the work note with a POST', () => {
    service.generarNotaTrabajo(7).subscribe();
    const req = httpMock.expectOne(`${base}/proformas/7/generar-nota-trabajo/`);
    expect(req.request.method).toBe('POST');
    req.flush({});
  });

  it('downloads the pdf as a blob', () => {
    let result: Blob | undefined;
    service.downloadProformaPdf(3).subscribe((blob) => (result = blob));
    const req = httpMock.expectOne(`${base}/proformas/3/pdf/`);
    expect(req.request.responseType).toBe('blob');
    req.flush(new Blob(['%PDF']));
    expect(result instanceof Blob).toBe(true);
  });

  it('turns a blob error of the pdf endpoint back into an object', async () => {
    let error: unknown;
    service.downloadProformaPdf(3).subscribe({ error: (e) => (error = e) });
    const req = httpMock.expectOne(`${base}/proformas/3/pdf/`);
    req.flush(new Blob([JSON.stringify({ detail: 'sin sucursal' })]), { status: 409, statusText: 'Conflict' });
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect((error as HttpErrorResponse).status).toBe(409);
    expect(extractApiError(error, 'fallback')).toBe('sin sucursal');
  });

  it('queries catalogs by sucursal', () => {
    service.listBobinas(4).subscribe();
    const bobinas = httpMock.expectOne((r) => r.url === `${base}/catalogo/bobinas`);
    expect(bobinas.request.params.get('sucursal')).toBe('4');
    bobinas.flush([]);

    service.listInstaladores(4).subscribe();
    httpMock.expectOne((r) => r.url === `${base}/catalogo/instaladores`).flush([]);

    service.listSucursales().subscribe();
    httpMock.expectOne(`${base}/catalogo/sucursales`).flush([]);
  });

  it('reads and updates work notes', () => {
    service.listNotasTrabajo('abc').subscribe();
    const list = httpMock.expectOne((r) => r.url === `${base}/notas-trabajo`);
    expect(list.request.params.get('search')).toBe('abc');
    list.flush([]);

    service.getNotaTrabajo(2).subscribe();
    httpMock.expectOne(`${base}/notas-trabajo/2/`).flush({});

    service.updateNotaTrabajo(2, { instaladar: null, codigo_garantia: '', salida_vehiculo: null, observaciones: '' }).subscribe();
    const patch = httpMock.expectOne(`${base}/notas-trabajo/2/`);
    expect(patch.request.method).toBe('PATCH');
    patch.flush({});
  });
});

describe('extractApiError', () => {
  it('flattens DRF field errors, line errors and detail', () => {
    expect(extractApiError({ error: { detail: 'boom' } }, 'x')).toBe('boom');
    expect(extractApiError({ error: { items: ['Línea 1: mal', 'Línea 2: peor'] } }, 'x')).toBe('Línea 1: mal Línea 2: peor');
    expect(extractApiError({ error: { discount: ['alto'], email: ['malo'] } }, 'x')).toBe('alto malo');
  });

  it('uses the fallback when there is no readable body', () => {
    expect(extractApiError({ error: null }, 'fallback')).toBe('fallback');
    expect(extractApiError(null, 'fallback')).toBe('fallback');
  });
});

describe('previewSubtotal', () => {
  it('matches the server formula for venta con instalacion', () => {
    // 1.75 * 3 * 120 + 50 * 3
    expect(previewSubtotal('venta_instalacion', 1.75, 3, 120, 50)).toBe(780);
  });

  it('matches the server formula for metro lineal (no quantity, no installation)', () => {
    expect(previewSubtotal('venta_metro_lineal', 3.5, 5, 120, 50)).toBe(420);
  });

  it('rounds to 2 decimals and returns 0 for incomplete data', () => {
    expect(previewSubtotal('venta_metro_lineal', 2.35, 0, 137.35, 0)).toBe(322.77);
    expect(previewSubtotal('venta_instalacion', 1, 0, 120, 50)).toBe(0);
    expect(previewSubtotal('venta_metro_lineal', NaN, 0, 120, 0)).toBe(0);
  });
});
