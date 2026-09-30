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
    is_close: false, nota_trabajo_id: null, nota_venta_id: null, email: 'a@b.com', ci_nit: '1', phone_number: '70000001',
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

  it('maps the status to the badge class and shows the server label', () => {
    create(detail());
    const cases: [string, string, string][] = [
      ['proforma', 'Proforma', 'status-proforma'],
      ['en_trabajo', 'En trabajo', 'status-progress'],
      ['por_cobrar', 'Por Cobrar', 'status-cobrar'],
      ['finalizado', 'Finalizado', 'status-final'],
      ['anulada', 'Anulada', 'status-void'],
    ];
    for (const [status, label, cssClass] of cases) {
      component.proforma = detail({ status: status as never, status_label: label });
      expect(component.statusText).toBe(label);
      expect(component.statusClass).toBe(cssClass);
    }
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
    create(detail({ is_close: true, status: 'en_trabajo', status_label: 'En trabajo' }));
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
      .flush(detail({ is_close: true, status: 'en_trabajo', status_label: 'En trabajo', nota_trabajo_id: 9 }));
    await pending;

    expect(component.proforma?.is_close).toBe(true);
    expect(component.proforma?.nota_trabajo_id).toBe(9);
  });

  it('shows the global status badge from the server label and class', () => {
    create(detail({ status: 'por_cobrar', status_label: 'Por Cobrar', is_close: true }));
    expect(component.statusText).toBe('Por Cobrar');
    expect(component.statusClass).toBe('status-cobrar');
    component.proforma = detail({ status: 'anulada', status_label: 'Anulada', is_close: true });
    expect(component.statusClass).toBe('status-void');
  });

  it('links to the nota de trabajo and nota de venta only while the order exists', () => {
    create(detail({ status: 'en_trabajo', is_close: true, nota_trabajo_id: 9, nota_venta_id: 4 }));
    expect(component.hasOrder).toBe(true);
    component.proforma = detail({ status: 'proforma', nota_trabajo_id: 9, nota_venta_id: 4 });
    expect(component.hasOrder).toBe(false);
    component.proforma = detail({ status: 'anulada', is_close: true });
    expect(component.hasOrder).toBe(false);
  });

  it('anular needs delete_proforma_header and a vigente proforma', () => {
    login(['product.delete_proforma_header']);
    create(detail());
    expect(component.canAnular).toBe(true);
    component.proforma = detail({ status: 'en_trabajo', is_close: true });
    expect(component.canAnular).toBe(false);
  });

  it('does not offer anular without the permission', () => {
    create(detail());
    expect(component.canAnular).toBe(false);
  });

  it('anula la proforma after confirming and refreshes it with the server response', async () => {
    login(['product.delete_proforma_header']);
    spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: true } as SweetAlertResult));
    create(detail());

    const pending = component.anular();
    await new Promise<void>((resolve) => setTimeout(resolve));
    const req = httpMock.expectOne(`${url}anular/`);
    expect(req.request.method).toBe('POST');
    req.flush(detail({ status: 'anulada', status_label: 'Anulada', is_close: true }));
    await pending;

    expect(component.proforma?.status).toBe('anulada');
  });
});
