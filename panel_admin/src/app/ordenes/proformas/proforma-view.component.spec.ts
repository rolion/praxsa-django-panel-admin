import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import Swal, { SweetAlertResult } from 'sweetalert2';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/service/auth.service';
import { AppProformaDetail } from '../ordenes.model';
import { ProformaViewComponent } from './proforma-view.component';

const detail = (overrides: Partial<AppProformaDetail> = {}): AppProformaDetail =>
  ({
    id: 5, sales_type: 'venta_metro_lineal', sales_type_label: 'Venta Metro Lineal', name: 'Ana',
    sucursal: 1, sucursal_name: 'Central', car_model_name: null, car_brand_name: null, car_plate: '',
    total_price: '420.00', discount: '0.00', total_a_pagar: '420.00',
    proforma_created_on: '2026-09-29T10:00:00', status: 'proforma', status_label: 'Proforma',
    is_close: false, nota_trabajo_id: null, email: 'a@b.com', ci_nit: '1', phone_number: '70000001',
    car_model_id: null, discount_reason: '', items: [], ...overrides,
  }) as AppProformaDetail;

describe('ProformaViewComponent', () => {
  let component: ProformaViewComponent;
  let httpMock: HttpTestingController;
  const url = `${environment.apiUrl}/product/ordenes/proformas/5/`;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [ProformaViewComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: '5' }) } } },
      ],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  function login(permissions: string[]): void {
    TestBed.inject(AuthService).login('u', 'p').subscribe();
    httpMock.expectOne(`${environment.apiUrl}/product/api-panel-admin-token-auth/`).flush({
      token: 't', user_id: 1, username: 'u', name: 'U', lastname: 'U', is_staff: true, groups: [], permissions,
    });
  }

  function create(proforma: AppProformaDetail) {
    const fixture = TestBed.createComponent(ProformaViewComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    httpMock.expectOne(url).flush(proforma);
    return fixture;
  }

  it('loads the proforma', () => {
    create(detail());
    expect(component.proforma?.id).toBe(5);
    expect(component.isInstalacion).toBe(false);
  });

  it('renders the detail in an ngx-datatable with a totals summary row', () => {
    const data = detail({
      sales_type: 'venta_instalacion',
      discount: '50.00', total_price: '728.00', total_a_pagar: '678.00',
      items: [{
        id: 1, car_part: 5, car_part_name: 'Parabrisas', window_film: 3, window_film_name: 'Carbon',
        width: '1.50', length: '1.20', quantity: 2, window_film_price: '120.00',
        installation_price: '50.00', sub_total: '388.00',
      }],
    });
    const fixture = create(data);
    fixture.detectChanges(); // dispara el ngOnInit del ciclo de vida: segunda carga
    httpMock.match(url).forEach((req) => req.flush(data));
    fixture.detectChanges();

    const element = fixture.nativeElement as HTMLElement;
    expect(element.querySelector('ngx-datatable')).not.toBeNull();
    expect(element.querySelector('table')).toBeNull();
    expect(component.isInstalacion).toBe(true);
    expect(component.noSummary()).toBe('');
  });

  it('shows an error when the proforma cannot be loaded (e.g. out of scope)', () => {
    const fixture = TestBed.createComponent(ProformaViewComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    httpMock.expectOne(url).flush({}, { status: 404, statusText: 'Not Found' });
    expect(component.errorMessage).toContain('No se pudo cargar');
  });

  it('edit and generate note need permission and an open proforma', () => {
    login(['product.change_proforma_header', 'product.add_nota_trabajo']);
    create(detail());
    expect(component.canEdit).toBe(true);
    expect(component.canGenerateNota).toBe(true);
  });

  it('hides edit and generate note for a closed proforma even with permissions', () => {
    login(['product.change_proforma_header', 'product.add_nota_trabajo']);
    create(detail({ is_close: true, status: 'nota_trabajo' }));
    expect(component.canEdit).toBe(false);
    expect(component.canGenerateNota).toBe(false);
  });

  it('hides edit and generate note without permissions', () => {
    create(detail());
    expect(component.canEdit).toBe(false);
    expect(component.canGenerateNota).toBe(false);
  });

  it('generates the note and refreshes the proforma with the server response', async () => {
    spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: true } as SweetAlertResult));
    create(detail());

    const pending = component.generateNota();
    await new Promise<void>((resolve) => setTimeout(resolve));
    httpMock
      .expectOne(`${url}generar-nota-trabajo/`)
      .flush(detail({ is_close: true, status: 'nota_trabajo', nota_trabajo_id: 9 }));
    await pending;

    expect(component.proforma?.is_close).toBe(true);
    expect(component.proforma?.nota_trabajo_id).toBe(9);
  });
});
