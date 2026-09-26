import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AppCarBrand } from '../vehicles.model';
import { ModelCreateComponent } from './model-create.component';

const sampleBrands: AppCarBrand[] = [{ id: 1, name: 'Toyota', is_active: true, models_count: 0 }];

describe('ModelCreateComponent', () => {
  let httpMock: HttpTestingController;
  const base = `${environment.apiUrl}/product/vehicles`;

  function createAndLoad() {
    const fixture = TestBed.createComponent(ModelCreateComponent);
    fixture.detectChanges();
    httpMock.expectOne((r) => r.url === `${base}/brands`).flush(sampleBrands);
    return fixture;
  }

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [ModelCreateComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('no envia el formulario sin marca seleccionada (invalido)', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;
    component.form.patchValue({ name: 'Corolla', car_brand_id: null });

    component.save();

    httpMock.expectNone(`${base}/models`);
    expect(component.form.invalid).toBe(true);
  });

  it('crea el modelo sin imagen (FormData sin la clave image)', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;
    component.form.setValue({ name: 'Corolla', car_brand_id: 1, image: null });

    component.save();

    const req = httpMock.expectOne(`${base}/models`);
    expect(req.request.body instanceof FormData).toBe(true);
    const body = req.request.body as FormData;
    expect(body.get('name')).toBe('Corolla');
    expect(body.get('car_brand_id')).toBe('1');
    expect(body.has('image')).toBe(false);
    req.flush({ id: 5, name: 'Corolla', car_brand_id: 1, car_brand_name: 'Toyota', image: null, is_active: true, items_count: 0 });
  });

  it('crea el modelo con imagen (FormData incluye el archivo)', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;
    const file = new File(['x'], 'foto.jpg', { type: 'image/jpeg' });
    component.form.setValue({ name: 'Corolla', car_brand_id: 1, image: file });

    component.save();

    const req = httpMock.expectOne(`${base}/models`);
    const body = req.request.body as FormData;
    expect(body.get('image')).toBe(file);
    req.flush({ id: 5, name: 'Corolla', car_brand_id: 1, car_brand_name: 'Toyota', image: null, is_active: true, items_count: 0 });
  });

  it('muestra el error del backend cuando la creacion falla', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;
    component.form.setValue({ name: 'Corolla', car_brand_id: 1, image: null });

    component.save();

    const req = httpMock.expectOne(`${base}/models`);
    req.flush({ name: ['Ya existe un modelo con este nombre.'] }, { status: 400, statusText: 'Bad Request' });

    expect(component.errorMessage).toBe('Ya existe un modelo con este nombre.');
    expect(component.saving).toBe(false);
  });
});
