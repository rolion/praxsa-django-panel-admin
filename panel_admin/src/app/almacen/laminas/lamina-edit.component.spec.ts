import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AppWindowFilm } from '../almacen.model';
import { LaminaEditComponent } from './lamina-edit.component';

const sampleLamina: AppWindowFilm = {
  id: 7, name: 'Carbon 20%', description: 'oscuro', content: null, image: 'http://x/img.jpg', is_active: true,
};

describe('LaminaEditComponent', () => {
  let httpMock: HttpTestingController;
  const base = `${environment.apiUrl}/product/almacen/laminas`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [LaminaEditComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: '7' }) } } },
      ],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function createAndLoad() {
    const fixture = TestBed.createComponent(LaminaEditComponent);
    fixture.detectChanges();
    httpMock.expectOne(`${base}/7/`).flush(sampleLamina);
    return fixture;
  }

  it('carga los datos de la lamina existente', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;

    expect(component.form.value.name).toBe('Carbon 20%');
    expect(component.currentImageUrl).toBe('http://x/img.jpg');
  });

  it('no manda la imagen si el usuario no la tocó (control no dirty)', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;
    component.form.patchValue({ description: 'nueva descripcion' });

    component.save();

    const req = httpMock.expectOne(`${base}/7/`);
    expect(req.request.body instanceof FormData).toBe(false);
    req.flush(sampleLamina);
  });

  it('manda la imagen como multipart cuando el usuario la reemplaza (dirty)', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;
    const file = new File(['x'], 'nuevo.jpg', { type: 'image/jpeg' });
    const imageControl = component.form.get('image')!;
    imageControl.setValue(file);
    imageControl.markAsDirty();

    component.save();

    const req = httpMock.expectOne(`${base}/7/`);
    expect(req.request.body instanceof FormData).toBe(true);
    req.flush(sampleLamina);
  });
});
