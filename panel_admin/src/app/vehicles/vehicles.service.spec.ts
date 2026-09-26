import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../environments/environment';
import { VehiclesService } from './vehicles.service';

describe('VehiclesService', () => {
  let service: VehiclesService;
  let httpMock: HttpTestingController;
  const base = `${environment.apiUrl}/product/vehicles`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(VehiclesService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('listBrands() sends search and include_inactive as query params', () => {
    service.listBrands({ search: 'toy', includeInactive: true }).subscribe();

    const req = httpMock.expectOne((r) => r.url === `${base}/brands`);
    expect(req.request.params.get('search')).toBe('toy');
    expect(req.request.params.get('include_inactive')).toBe('true');
    req.flush([]);
  });

  it('listBrands() omits query params when not requested', () => {
    service.listBrands().subscribe();

    const req = httpMock.expectOne((r) => r.url === `${base}/brands`);
    expect(req.request.params.has('search')).toBe(false);
    expect(req.request.params.has('include_inactive')).toBe(false);
    req.flush([]);
  });

  it('listModels() sends car_brand_id as a query param', () => {
    service.listModels({ carBrandId: 5 }).subscribe();

    const req = httpMock.expectOne((r) => r.url === `${base}/models`);
    expect(req.request.params.get('car_brand_id')).toBe('5');
    req.flush([]);
  });

  it('createModel() sends a multipart FormData with name, car_brand_id and image', () => {
    const file = new File(['x'], 'foto.jpg', { type: 'image/jpeg' });
    service.createModel('Corolla', 3, file).subscribe();

    const req = httpMock.expectOne(`${base}/models`);
    expect(req.request.body).toBeInstanceOf(FormData);
    const body = req.request.body as FormData;
    expect(body.get('name')).toBe('Corolla');
    expect(body.get('car_brand_id')).toBe('3');
    expect(body.get('image')).toBe(file);
    req.flush({});
  });

  it('createModel() omits the image field when none is given', () => {
    service.createModel('Corolla', 3).subscribe();

    const req = httpMock.expectOne(`${base}/models`);
    const body = req.request.body as FormData;
    expect(body.has('image')).toBe(false);
    req.flush({});
  });

  it('updateModel() sends plain JSON when the image is not touched (undefined)', () => {
    service.updateModel(1, 'Corolla', 3, undefined).subscribe();

    const req = httpMock.expectOne(`${base}/models/1/`);
    expect(req.request.body).toEqual({ name: 'Corolla', car_brand_id: 3 });
    req.flush({});
  });

  it('updateModel() sends an empty image field when removing the image (null)', () => {
    service.updateModel(1, 'Corolla', 3, null).subscribe();

    const req = httpMock.expectOne(`${base}/models/1/`);
    const body = req.request.body as FormData;
    expect(body.get('image')).toBe('');
    req.flush({});
  });

  it('addModelItem() posts the payload to the model items endpoint', () => {
    const payload = {
      car_part_id: 7,
      width: '1.50',
      length: '1.00',
      quantity: 1,
      installation_price: '80.00',
    };
    service.addModelItem(4, payload).subscribe();

    const req = httpMock.expectOne(`${base}/models/4/items/`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(payload);
    req.flush({});
  });

  it('removeModelItem() deletes the specific association', () => {
    service.removeModelItem(4, 9).subscribe();

    const req = httpMock.expectOne(`${base}/models/4/items/9/`);
    expect(req.request.method).toBe('DELETE');
    req.flush(null);
  });
});
