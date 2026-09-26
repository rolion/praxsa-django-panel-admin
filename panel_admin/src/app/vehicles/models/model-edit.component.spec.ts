import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';
import { ImageUploadComponent } from '../../shared/image-upload/image-upload.component';
import { AppCarModel } from '../vehicles.model';
import { ModelEditComponent } from './model-edit.component';

const sampleModel: AppCarModel = {
  id: 7,
  name: 'Corolla',
  car_brand_id: 3,
  car_brand_name: 'Toyota',
  image: 'http://localhost:8000/media/car_models/corolla.jpg',
  is_active: true,
  items_count: 0,
};

describe('ModelEditComponent', () => {
  let httpMock: HttpTestingController;
  const base = `${environment.apiUrl}/product/vehicles`;

  function createAndLoad() {
    const fixture = TestBed.createComponent(ModelEditComponent);
    fixture.detectChanges();
    httpMock.expectOne(`${base}/models/7/`).flush(sampleModel);
    httpMock.expectOne((r) => r.url === `${base}/brands`).flush([]);
    fixture.detectChanges();
    return fixture;
  }

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [ModelEditComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => '7' } } },
        },
      ],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('muestra la imagen existente del modelo en el formulario', () => {
    const fixture = createAndLoad();

    const img = fixture.nativeElement.querySelector('app-image-upload img');
    expect(img).withContext('la imagen existente deberia renderizarse').toBeTruthy();
    expect(img.getAttribute('src')).toBe(sampleModel.image);
  });

  it('guardar sin tocar la imagen no envia el campo image (no debe borrarla)', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;

    component.save();

    const req = httpMock.expectOne(`${base}/models/7/`);
    expect(req.request.body instanceof FormData).toBe(false);
    expect(req.request.body).toEqual({ name: 'Corolla', car_brand_id: 3 });
    req.flush(sampleModel);
  });

  it('seleccionar una imagen nueva la envia en el PATCH', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;
    const imageUpload = fixture.debugElement.query(By.directive(ImageUploadComponent))
      .componentInstance as ImageUploadComponent;
    const newFile = new File(['x'], 'nuevo.jpg', { type: 'image/jpeg' });

    imageUpload.onFileSelected({ target: { files: [newFile] } } as unknown as Event);
    component.save();

    const req = httpMock.expectOne(`${base}/models/7/`);
    expect(req.request.body instanceof FormData).toBe(true);
    expect((req.request.body as FormData).get('image')).toBe(newFile);
    req.flush(sampleModel);
  });

  it('quitar la imagen existente la borra al guardar', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;
    const imageUpload = fixture.debugElement.query(By.directive(ImageUploadComponent))
      .componentInstance as ImageUploadComponent;

    imageUpload.removeImage();
    component.save();

    const req = httpMock.expectOne(`${base}/models/7/`);
    expect(req.request.body instanceof FormData).toBe(true);
    expect((req.request.body as FormData).get('image')).toBe('');
    req.flush(sampleModel);
  });
});
