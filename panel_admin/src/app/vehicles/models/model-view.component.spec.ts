import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AppCarModel, AppCarModelPart } from '../vehicles.model';
import { ModelViewComponent } from './model-view.component';

const sampleModel: AppCarModel = {
  id: 5,
  name: 'Corolla',
  car_brand_id: 1,
  car_brand_name: 'Toyota',
  image: null,
  is_active: true,
  items_count: 1,
};

const sampleItem: AppCarModelPart = {
  id: 9,
  car_part_id: 2,
  car_part_name: 'Parabrisas',
  width: '1.00',
  length: '1.00',
  quantity: 1,
  installation_price: '50.00',
};

describe('ModelViewComponent', () => {
  let httpMock: HttpTestingController;
  const base = `${environment.apiUrl}/product/vehicles`;

  function createAndLoad() {
    const fixture = TestBed.createComponent(ModelViewComponent);
    fixture.detectChanges();
    httpMock.expectOne(`${base}/models/5/`).flush(sampleModel);
    httpMock.expectOne(`${base}/models/5/items/`).flush([sampleItem]);
    fixture.detectChanges();
    return fixture;
  }

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [ModelViewComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => '5' } } },
        },
      ],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('muestra el placeholder si la imagen del modelo no carga', () => {
    const fixture = TestBed.createComponent(ModelViewComponent);
    fixture.detectChanges();
    httpMock
      .expectOne(`${base}/models/5/`)
      .flush({ ...sampleModel, image: 'http://localhost:8000/media/car_models/x.jpg' });
    httpMock.expectOne(`${base}/models/5/items/`).flush([sampleItem]);
    fixture.detectChanges();
    const img = fixture.nativeElement.querySelector('img') as HTMLImageElement;
    expect(img).withContext('con imagen debe renderizar <img>').toBeTruthy();

    img.dispatchEvent(new Event('error'));
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('img')).toBeNull();
    expect(fixture.nativeElement.querySelector('.fa-image')).toBeTruthy();
  });

  it('reintenta la imagen del modelo al recargarlo tras un fallo', () => {
    const fixture = TestBed.createComponent(ModelViewComponent);
    fixture.detectChanges();
    httpMock
      .expectOne(`${base}/models/5/`)
      .flush({ ...sampleModel, image: 'http://localhost:8000/media/car_models/x.jpg' });
    httpMock.expectOne(`${base}/models/5/items/`).flush([sampleItem]);
    fixture.detectChanges();
    fixture.nativeElement.querySelector('img').dispatchEvent(new Event('error'));
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('img')).toBeNull();

    fixture.componentInstance.load();
    httpMock
      .expectOne(`${base}/models/5/`)
      .flush({ ...sampleModel, image: 'http://localhost:8000/media/car_models/x.jpg' });
    httpMock.expectOne(`${base}/models/5/items/`).flush([sampleItem]);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('img')).toBeTruthy();
  });

  it('muestra el contador de items asociados en singular y plural', () => {
    const fixture = createAndLoad();
    const counter = () =>
      (fixture.nativeElement.querySelector('[data-test="items-count"]') as HTMLElement).textContent?.trim();
    expect(counter()).toBe('1 Ítem Asociado');

    fixture.componentInstance.items = [sampleItem, { ...sampleItem, id: 10, car_part_id: 3 }];
    fixture.detectChanges();
    expect(counter()).toBe('2 Ítems Asociados');
  });

  it('muestra el estado como pill Activo / Inactivo', () => {
    const fixture = createAndLoad();
    const status = () => fixture.nativeElement.querySelector('[data-test="status"]') as HTMLElement;
    expect(status().textContent?.trim()).toBe('Activo');
    expect(status().classList).toContain('bg-success-subtle');

    fixture.componentInstance.model = { ...sampleModel, is_active: false };
    fixture.detectChanges();
    expect(status().textContent?.trim()).toBe('Inactivo');
    expect(status().classList).toContain('bg-secondary-subtle');
  });

  it('el boton Editar del modelo enlaza a la edicion', () => {
    const fixture = createAndLoad();
    const link = fixture.nativeElement.querySelector('[data-test="edit-model"]') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toBe('/vehicles/models/edit/5');
  });

  it('sin items muestra el estado vacio y ninguna tarjeta', () => {
    const fixture = TestBed.createComponent(ModelViewComponent);
    fixture.detectChanges();
    httpMock.expectOne(`${base}/models/5/`).flush(sampleModel);
    httpMock.expectOne(`${base}/models/5/items/`).flush([]);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('app-model-item-card')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('todavía no tiene items asociados');
    expect(fixture.nativeElement.querySelector('[data-test="items-count"]').textContent.trim()).toBe(
      '0 Ítems Asociados'
    );
  });

  it('carga el modelo y sus items', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;

    expect(component.model).toEqual(sampleModel);
    expect(component.items).toEqual([sampleItem]);
  });

  it('agregar item existente no manda installation_price (queda oculto)', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;
    component.mode = 'existing';
    component.addForm.setValue({ car_part_id: 2, new_car_part_name: '', width: '1.5', length: '1.0', quantity: 1 });

    component.saveItem();

    const req = httpMock.expectOne(`${base}/models/5/items/`);
    expect(req.request.body.installation_price).toBeUndefined();
    expect(req.request.body).toEqual({ car_part_id: 2, width: '1.5', length: '1.0', quantity: 1 });
    req.flush(sampleItem);
    httpMock.expectOne(`${base}/models/5/`).flush(sampleModel);
    httpMock.expectOne(`${base}/models/5/items/`).flush([sampleItem]);
  });

  function clickEditButton(fixture: ReturnType<typeof createAndLoad>) {
    const editButton = fixture.nativeElement.querySelector(
      'app-model-item-card button[title="Editar"]'
    ) as HTMLButtonElement;
    editButton.click();
  }

  it('abrir "editar item" precarga ancho/largo/cantidad del item', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;

    clickEditButton(fixture);

    expect(component.editForm.value).toEqual({ width: '1.00', length: '1.00', quantity: 1 });
    expect(component.editingItem).toEqual(sampleItem);
  });

  it('guardar la edicion manda solo ancho/largo/cantidad (no cambia el item ni el precio)', () => {
    const fixture = createAndLoad();
    const component = fixture.componentInstance;
    clickEditButton(fixture);
    component.editForm.patchValue({ width: '2.00', quantity: 3 });

    component.saveEditItem();

    const req = httpMock.expectOne(`${base}/models/5/items/9/`);
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ width: '2.00', length: '1.00', quantity: 3 });
    req.flush({ ...sampleItem, width: '2.00', quantity: 3 });
    httpMock.expectOne(`${base}/models/5/`).flush(sampleModel);
    httpMock.expectOne(`${base}/models/5/items/`).flush([sampleItem]);
  });
});
