import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AppCarModel } from '../vehicles.model';
import { ModelsListComponent } from './models-list.component';

const sampleModels: AppCarModel[] = [
  {
    id: 1,
    name: 'Corolla',
    car_brand_id: 1,
    car_brand_name: 'Toyota',
    image: null,
    is_active: true,
    items_count: 2,
  },
  {
    id: 2,
    name: 'Sentra',
    car_brand_id: 2,
    car_brand_name: 'Nissan',
    image: null,
    is_active: true,
    items_count: 0,
  },
];

describe('ModelsListComponent', () => {
  let component: ModelsListComponent;
  let httpMock: HttpTestingController;
  const base = `${environment.apiUrl}/product/vehicles/models`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [ModelsListComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    const fixture = TestBed.createComponent(ModelsListComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('loads models from the API into rows', () => {
    const req = httpMock.expectOne((r) => r.url === base);
    req.flush(sampleModels);

    expect(component.rows).toEqual(sampleModels);
  });

  it('filterDatatable() matches by model name', () => {
    httpMock.expectOne((r) => r.url === base).flush(sampleModels);

    component.filterDatatable({ target: { value: 'corolla' } } as unknown as Event);

    expect(component.rows.map((r) => r.name)).toEqual(['Corolla']);
  });

  it('filterDatatable() also matches by brand name', () => {
    httpMock.expectOne((r) => r.url === base).flush(sampleModels);

    component.filterDatatable({ target: { value: 'nissan' } } as unknown as Event);

    expect(component.rows.map((r) => r.name)).toEqual(['Sentra']);
  });
});
