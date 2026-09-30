import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
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
  let fixture: ComponentFixture<ModelsListComponent>;
  let httpMock: HttpTestingController;
  const base = `${environment.apiUrl}/product/vehicles/models`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [ModelsListComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    fixture = TestBed.createComponent(ModelsListComponent);
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

  it('muestra el placeholder cuando la imagen de un modelo falla al cargar', () => {
    const withImage = [{ ...sampleModels[0], image: 'http://localhost:8000/media/car_models/x.jpg' }];
    // detectChanges() dispara un ngOnInit extra (el beforeEach ya llamo uno a mano).
    fixture.detectChanges();
    httpMock.match((r) => r.url === base).forEach((req) => req.flush(withImage));
    fixture.detectChanges();
    const img = fixture.nativeElement.querySelector('img.data-table-img') as HTMLImageElement;
    expect(img).withContext('con imagen debe renderizar <img>').toBeTruthy();

    img.dispatchEvent(new Event('error'));
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('img.data-table-img')).toBeNull();
    expect(component.failedImageIds.has(withImage[0].id)).toBeTrue();
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
