import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';
import { LaminaCreateComponent } from './lamina-create.component';

describe('LaminaCreateComponent', () => {
  let httpMock: HttpTestingController;
  const base = `${environment.apiUrl}/product/almacen/laminas`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [LaminaCreateComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function createComponent() {
    const fixture = TestBed.createComponent(LaminaCreateComponent);
    fixture.detectChanges();
    return fixture;
  }

  it('no envia el formulario sin descripcion (invalido)', () => {
    const fixture = createComponent();
    const component = fixture.componentInstance;
    component.form.patchValue({ name: 'Carbon 20%', description: '' });

    component.save();

    httpMock.expectNone(base);
    expect(component.form.invalid).toBe(true);
  });

  it('crea la lamina sin imagen (JSON, sin multipart)', () => {
    const fixture = createComponent();
    const component = fixture.componentInstance;
    component.form.setValue({ name: 'Carbon 20%', description: 'oscuro', image: null });

    component.save();

    const req = httpMock.expectOne(base);
    expect(req.request.body instanceof FormData).toBe(false);
    expect(req.request.body).toEqual({ name: 'Carbon 20%', description: 'oscuro' });
    req.flush({ id: 1, name: 'Carbon 20%', description: 'oscuro', content: null, image: null, is_active: true });
  });

  it('crea la lamina con imagen (FormData incluye el archivo)', () => {
    const fixture = createComponent();
    const component = fixture.componentInstance;
    const file = new File(['x'], 'foto.jpg', { type: 'image/jpeg' });
    component.form.setValue({ name: 'Carbon 20%', description: 'oscuro', image: file });

    component.save();

    const req = httpMock.expectOne(base);
    const body = req.request.body as FormData;
    expect(body.get('image')).toBe(file);
    req.flush({ id: 1, name: 'Carbon 20%', description: 'oscuro', content: null, image: null, is_active: true });
  });

  it('muestra el error del backend cuando la creacion falla', () => {
    const fixture = createComponent();
    const component = fixture.componentInstance;
    component.form.setValue({ name: 'Carbon 20%', description: 'oscuro', image: null });

    component.save();

    httpMock.expectOne(base).flush({ image: ['Formato de imagen no permitido. Use JPG, PNG o WEBP.'] }, { status: 400, statusText: 'Bad Request' });

    expect(component.errorMessage).toBe('Formato de imagen no permitido. Use JPG, PNG o WEBP.');
    expect(component.saving).toBe(false);
  });
});
