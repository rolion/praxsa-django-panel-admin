import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/service/auth.service';
import { AppNotaTrabajo, AppNotaTrabajoDetail } from '../ordenes.model';
import { NotaTrabajoViewComponent } from './nota-trabajo-view.component';
import { NotasTrabajoListComponent } from './notas-trabajo-list.component';

const base = `${environment.apiUrl}/product/ordenes`;

const nota = (overrides: Partial<AppNotaTrabajoDetail> = {}): AppNotaTrabajoDetail => ({
  id: 3, proforma_id: 5, name: 'Ana', car_model_name: 'Corolla', car_plate: 'ABC123', instaladar: null,
  instalador_name: null, codigo_garantia: null, entrada_vehiculo: '2026-09-29T10:00:00',
  salida_vehiculo: null, sucursal_id: 1, sucursal_name: 'Central', is_close: false, is_finalizada: false,
  observaciones: null, responsable_name: 'oscar', sales_type: 'venta_instalacion',
  sales_type_label: 'Venta con Instalación', resumen: [], proforma_items: [], ...overrides,
});

function routeWithId(id: string) {
  return { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id }) } } };
}

function login(httpMock: HttpTestingController, permissions: string[]): void {
  TestBed.inject(AuthService).login('u', 'p').subscribe();
  httpMock.expectOne(`${environment.apiUrl}/product/api-panel-admin-token-auth/`).flush({
    token: 't', user_id: 1, username: 'u', name: 'U', lastname: 'U', is_staff: true, groups: [], permissions,
  });
}

describe('NotasTrabajoListComponent', () => {
  let httpMock: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [NotasTrabajoListComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('loads and filters client side; edit needs permission', () => {
    login(httpMock, ['product.change_nota_trabajo']);
    const component = TestBed.createComponent(NotasTrabajoListComponent).componentInstance;
    component.ngOnInit();
    const rows: AppNotaTrabajo[] = [nota(), nota({ id: 4, proforma_id: 6, name: 'Luis', car_plate: 'ZZZ999' })];
    httpMock.expectOne(`${base}/notas-trabajo`).flush(rows);

    expect(component.rows.length).toBe(2);
    component.filterDatatable({ target: { value: 'zzz' } } as unknown as Event);
    expect(component.rows.map((r) => r.id)).toEqual([4]);
    expect(component.canEdit).toBe(true);
  });

  it('shows the missing sucursal state when empty and the user has none', () => {
    const component = TestBed.createComponent(NotasTrabajoListComponent).componentInstance;
    component.ngOnInit();
    httpMock.expectOne(`${base}/notas-trabajo`).flush([]);
    httpMock.expectOne(`${base}/catalogo/sucursales`).flush([]);

    expect(component.withoutSucursal).toBe(true);
    expect(component.canEdit).toBe(false);
  });
});

describe('NotaTrabajoViewComponent', () => {
  let httpMock: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [NotaTrabajoViewComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), routeWithId('3')],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('can edit only with permission and while not finalized', () => {
    login(httpMock, ['product.change_nota_trabajo']);
    const component = TestBed.createComponent(NotaTrabajoViewComponent).componentInstance;
    component.ngOnInit();
    httpMock.expectOne(`${base}/notas-trabajo/3/`).flush(nota());
    expect(component.canEdit).toBe(true);

    component.nota = nota({ is_finalizada: true });
    expect(component.canEdit).toBe(false);
  });

  it('shows the status badge: en ejecucion until the nota de venta exists, then finalizado', () => {
    const component = TestBed.createComponent(NotaTrabajoViewComponent).componentInstance;
    component.ngOnInit();
    httpMock.expectOne(`${base}/notas-trabajo/3/`).flush(nota());

    expect(component.statusText).toBe('En ejecución');
    expect(component.statusClass).toBe('status-progress');

    component.nota = nota({ is_finalizada: true });
    expect(component.statusText).toBe('Finalizado');
    expect(component.statusClass).toBe('status-done');
  });

  it('renders cards, formatted dates, muted empty values and the detail tables', () => {
    const fixture = TestBed.createComponent(NotaTrabajoViewComponent);
    const component = fixture.componentInstance;
    const data = nota({
      entrada_vehiculo: '2025-08-05T04:16:51',
      proforma_items: [{
        id: 1, car_part: 5, car_part_name: 'Parabrisas', window_film: 3, window_film_name: 'Carbon',
        width: '1.50', length: '1.20', quantity: 2, window_film_price: '120.00',
        installation_price: '50.00', sub_total: '388.00',
      }],
      resumen: [{ window_film_name: 'Carbon', width: '1.50', length: '2.40' }],
    });
    component.ngOnInit();
    httpMock.expectOne(`${base}/notas-trabajo/3/`).flush(data);
    fixture.detectChanges(); // ngOnInit del ciclo de vida: segunda carga
    httpMock.match(`${base}/notas-trabajo/3/`).forEach((req) => req.flush(data));
    fixture.detectChanges();

    const element = fixture.nativeElement as HTMLElement;
    expect(element.querySelectorAll('.section-card').length).toBe(5);
    expect(element.querySelectorAll('ngx-datatable').length).toBe(2);
    expect(element.querySelector('table')).toBeNull();
    const text = element.textContent || '';
    expect(text).toContain('05/08/2025 - 04:16 h');
    expect(text).toContain('Sin código');
    expect(text).toContain('Aún no registrada');
    expect(text).toContain('Sin observaciones');
  });

  it('cannot edit without permission', () => {
    const component = TestBed.createComponent(NotaTrabajoViewComponent).componentInstance;
    component.ngOnInit();
    httpMock.expectOne(`${base}/notas-trabajo/3/`).flush(nota());
    expect(component.canEdit).toBe(false);
  });
});

describe('NotaTrabajoViewComponent in-situ editing', () => {
  let httpMock: HttpTestingController;
  let router: Router;

  function setup(data?: Record<string, unknown>) {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [NotaTrabajoViewComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ id: '3' }), data: data ?? {} } },
        },
      ],
    });
    httpMock = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
  }

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  function create(detail: AppNotaTrabajoDetail, permissions = ['product.change_nota_trabajo']) {
    if (permissions.length) {
      login(httpMock, permissions);
    }
    const component = TestBed.createComponent(NotaTrabajoViewComponent).componentInstance;
    component.ngOnInit();
    httpMock.expectOne(`${base}/notas-trabajo/3/`).flush(detail);
    return component;
  }

  it('starts in read mode and "Editar" turns the operational fields into inputs preloaded with the saved values', () => {
    setup();
    const component = create(
      nota({ codigo_garantia: 'GAR-1', observaciones: 'ok', salida_vehiculo: '2026-09-30T15:30:00', instaladar: 7 })
    );
    expect(component.editing).toBe(false);

    component.startEdit();
    httpMock
      .expectOne((r) => r.url === `${base}/catalogo/instaladores` && r.params.get('sucursal') === '1')
      .flush([{ id: 7, name: 'Pedro' }]);

    expect(component.editing).toBe(true);
    expect(component.form.value).toEqual({
      codigo_garantia: 'GAR-1', instaladar: 7, salida_vehiculo: '2026-09-30T15:30', observaciones: 'ok',
    });
    expect(component.instaladores.length).toBe(1);
  });

  it('cannot start editing without permission or when the note is finalized', () => {
    setup();
    const component = create(nota(), []);
    component.startEdit();
    expect(component.editing).toBe(false);

    component.nota = nota({ is_finalizada: true });
    component.startEdit();
    expect(component.editing).toBe(false);
  });

  it('cancel discards the changes and restores the original values', () => {
    setup();
    const component = create(nota({ codigo_garantia: 'GAR-1', observaciones: 'original' }));
    component.startEdit();
    httpMock.expectOne((r) => r.url === `${base}/catalogo/instaladores`).flush([]);
    component.form.patchValue({ codigo_garantia: 'CAMBIADO', observaciones: 'otro' });

    component.cancelEdit();

    expect(component.editing).toBe(false);
    expect(component.form.value.codigo_garantia).toBe('GAR-1');
    expect(component.form.value.observaciones).toBe('original');
    expect(component.nota?.codigo_garantia).toBe('GAR-1');
  });

  it('saves only the operational fields, refreshes the note and leaves edit mode', () => {
    setup();
    const component = create(nota());
    component.startEdit();
    httpMock.expectOne((r) => r.url === `${base}/catalogo/instaladores`).flush([{ id: 7, name: 'Pedro' }]);
    component.form.patchValue({ instaladar: 7, codigo_garantia: ' GAR-2 ', observaciones: 'listo' });

    component.save();

    const req = httpMock.expectOne(`${base}/notas-trabajo/3/`);
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({
      instaladar: 7, codigo_garantia: 'GAR-2', salida_vehiculo: null, observaciones: 'listo',
    });
    req.flush(nota({ instaladar: 7, instalador_name: 'Pedro', codigo_garantia: 'GAR-2', observaciones: 'listo' }));

    expect(component.editing).toBe(false);
    expect(component.nota?.instalador_name).toBe('Pedro');
    expect(component.savedMessage).toBe('Cambios guardados.');
  });

  it('does not submit a garantia code longer than 12 characters', () => {
    setup();
    const component = create(nota());
    component.startEdit();
    httpMock.expectOne((r) => r.url === `${base}/catalogo/instaladores`).flush([]);
    component.form.patchValue({ codigo_garantia: 'X'.repeat(13) });

    component.save();

    httpMock.expectNone(`${base}/notas-trabajo/3/`);
    expect(component.editing).toBe(true);
  });

  it('keeps edit mode and shows the server error (e.g. duplicated garantia code)', () => {
    setup();
    const component = create(nota());
    component.startEdit();
    httpMock.expectOne((r) => r.url === `${base}/catalogo/instaladores`).flush([]);
    component.form.patchValue({ codigo_garantia: 'DUP' });

    component.save();
    httpMock
      .expectOne(`${base}/notas-trabajo/3/`)
      .flush({ codigo_garantia: ['ya existe'] }, { status: 400, statusText: 'Bad Request' });

    expect(component.editing).toBe(true);
    expect(component.saveError).toBe('ya existe');
    expect(component.saving).toBe(false);
  });

  it('the edit route opens the view already in edit mode', () => {
    setup({ edit: true });
    const component = create(nota());
    httpMock.expectOne((r) => r.url === `${base}/catalogo/instaladores`).flush([]);
    expect(component.editing).toBe(true);
  });

  it('the edit route stays read-only when the note is already finalized', () => {
    setup({ edit: true });
    const component = create(nota({ is_finalizada: true }));
    expect(component.editing).toBe(false);
  });

  it('the edit route goes back to the view URL after cancel', () => {
    setup({ edit: true });
    const component = create(nota());
    httpMock.expectOne((r) => r.url === `${base}/catalogo/instaladores`).flush([]);

    component.cancelEdit();

    expect(router.navigate).toHaveBeenCalledWith(['/ordenes/notas-trabajo/view', 3]);
  });
});
