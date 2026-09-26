import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import Swal, { SweetAlertResult } from 'sweetalert2';
import { environment } from '../../../environments/environment';
import { AppCarPart } from '../vehicles.model';
import { PartsListComponent } from './parts-list.component';

const sampleParts: AppCarPart[] = [
  { id: 1, name: 'Parabrisas delantero', is_active: true },
  { id: 2, name: 'Ventana lateral', is_active: true },
];

describe('PartsListComponent', () => {
  let component: PartsListComponent;
  let httpMock: HttpTestingController;
  const base = `${environment.apiUrl}/product/vehicles/parts`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [PartsListComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    const fixture = TestBed.createComponent(PartsListComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('loads parts from the API into rows', () => {
    const req = httpMock.expectOne((r) => r.url === base);
    req.flush(sampleParts);

    expect(component.rows).toEqual(sampleParts);
    expect(component.loadingIndicator).toBe(false);
  });

  it('filterDatatable() filters rows by name and resets on empty term', () => {
    httpMock.expectOne((r) => r.url === base).flush(sampleParts);

    component.filterDatatable({ target: { value: 'ventana' } } as unknown as Event);
    expect(component.rows.map((r) => r.name)).toEqual(['Ventana lateral']);

    component.filterDatatable({ target: { value: '' } } as unknown as Event);
    expect(component.rows.length).toBe(2);
  });

  it('deactivate() confirms and calls toggle-active with false', () => {
    httpMock.expectOne((r) => r.url === base).flush(sampleParts);
    spyOn(Swal, 'fire').and.returnValue(
      Promise.resolve({ isConfirmed: true } as SweetAlertResult)
    );

    component.deactivate(sampleParts[0]);

    return Promise.resolve().then(() => {
      const req = httpMock.expectOne(`${base}/1/toggle-active/`);
      expect(req.request.body).toEqual({ is_active: false });
      req.flush({ ...sampleParts[0], is_active: false });
      httpMock.expectOne((r) => r.url === base).flush([]);
    });
  });
});
