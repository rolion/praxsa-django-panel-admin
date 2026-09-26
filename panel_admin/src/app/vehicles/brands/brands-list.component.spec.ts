import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import Swal, { SweetAlertResult } from 'sweetalert2';
import { environment } from '../../../environments/environment';
import { AppCarBrand } from '../vehicles.model';
import { BrandsListComponent } from './brands-list.component';

const sampleBrands: AppCarBrand[] = [
  { id: 1, name: 'Toyota', is_active: true, models_count: 2 },
  { id: 2, name: 'Nissan', is_active: true, models_count: 0 },
];

describe('BrandsListComponent', () => {
  let component: BrandsListComponent;
  let httpMock: HttpTestingController;
  const base = `${environment.apiUrl}/product/vehicles/brands`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [BrandsListComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    const fixture = TestBed.createComponent(BrandsListComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('loads brands from the API into rows', () => {
    const req = httpMock.expectOne((r) => r.url === base);
    req.flush(sampleBrands);

    expect(component.rows).toEqual(sampleBrands);
    expect(component.loadingIndicator).toBe(false);
  });

  it('filterDatatable() filters rows by name (case-insensitive substring)', () => {
    httpMock.expectOne((r) => r.url === base).flush(sampleBrands);

    component.filterDatatable({ target: { value: 'toy' } } as unknown as Event);

    expect(component.rows.map((r) => r.name)).toEqual(['Toyota']);
  });

  it('filterDatatable() with an empty term restores every row', () => {
    httpMock.expectOne((r) => r.url === base).flush(sampleBrands);
    component.filterDatatable({ target: { value: 'toy' } } as unknown as Event);

    component.filterDatatable({ target: { value: '' } } as unknown as Event);

    expect(component.rows.length).toBe(2);
  });

  it('deactivate() confirms and calls toggle-active with false', () => {
    httpMock.expectOne((r) => r.url === base).flush(sampleBrands);
    spyOn(Swal, 'fire').and.returnValue(
      Promise.resolve({ isConfirmed: true } as SweetAlertResult)
    );

    component.deactivate(sampleBrands[0]);

    return Promise.resolve().then(() => {
      const req = httpMock.expectOne(`${base}/1/toggle-active/`);
      expect(req.request.body).toEqual({ is_active: false });
      req.flush({ ...sampleBrands[0], is_active: false });
      httpMock.expectOne((r) => r.url === base).flush([]);
    });
  });
});
