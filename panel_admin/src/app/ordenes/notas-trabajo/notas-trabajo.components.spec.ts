import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import Swal, { SweetAlertResult } from 'sweetalert2';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/service/auth.service';
import { AppNotaTrabajo, AppNotaTrabajoDetail } from '../ordenes.model';
import { NotaTrabajoViewComponent } from './nota-trabajo-view.component';
import { NotasTrabajoListComponent } from './notas-trabajo-list.component';

const base = `${environment.apiUrl}/product/ordenes`;

const nota = (overrides: Partial<AppNotaTrabajoDetail> = {}): AppNotaTrabajoDetail => ({
  id: 3, proforma_id: 5, name: 'Ana', car_model_name: 'Corolla', car_plate: 'ABC123', instaladar: null,
  instalador_name: null, codigo_garantia: null, entrada_vehiculo: '2026-09-29T10:00:00',
  salida_vehiculo: null, sucursal_id: 1, sucursal_name: 'Central', is_close: false, status: 'en_proceso', status_label: 'En proceso',
  nota_venta: { id: 7, status: 'por_cobrar', status_label: 'Por cobrar', total_price: '340.00' },
  observaciones: null, responsable_name: 'oscar', sales_type: 'venta_instalacion',
  sales_type_label: 'Venta con Instalación', resumen: [], proforma_items: [], ...overrides,
});

const ev = (value: string) => ({ target: { value } }) as unknown as Event;

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

describe('NotasTrabajoListComponent filtros', () => {
  let httpMock: HttpTestingController;
  let component: NotasTrabajoListComponent;

  const nv = (status: 'por_cobrar' | 'pagada' | 'anulada') => ({ id: 1, status, status_label: status, total_price: '1.00' });
  const rows = (): AppNotaTrabajo[] => [
    nota({ id: 1, sucursal_id: 1, sucursal_name: 'Central', car_brand_name: 'Toyota', car_model_name: 'Corolla', instaladar: 10, instalador_name: 'Pedro', status: 'en_proceso', nota_venta: nv('por_cobrar') }),
    nota({ id: 2, sucursal_id: 2, sucursal_name: 'Norte', car_brand_name: 'Toyota', car_model_name: 'Hilux', instaladar: 11, instalador_name: 'Juan', status: 'terminado', nota_venta: nv('pagada') }),
    nota({ id: 3, sucursal_id: 2, sucursal_name: 'Norte', car_brand_name: 'Nissan', car_model_name: 'Sentra', instaladar: null, instalador_name: null, status: 'cancelada', nota_venta: null }),
  ];
  const ids = () => component.rows.map((r) => r.id);

  function create(data: AppNotaTrabajo[]) {
    const fixture = TestBed.createComponent(NotasTrabajoListComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    httpMock.expectOne(`${base}/notas-trabajo`).flush(data);
    return fixture;
  }

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

  it('offers sucursales, brands, models and installers from the loaded rows', () => {
    create(rows());
    expect(component.sucursalOptions.map((o) => o.label)).toEqual(['Central', 'Norte']);
    expect(component.marcaOptions).toEqual(['Nissan', 'Toyota']);
    expect(component.modeloOptions).toEqual(['Corolla', 'Hilux', 'Sentra']);
    expect(component.instaladorOptions.map((o) => o.label)).toEqual(['Juan', 'Pedro']);
  });

  it('filters by sucursal, brand, model, installer, state and cobro', () => {
    create(rows());
    component.setFiltro('sucursal', ev('2'));
    expect(ids()).toEqual([2, 3]);
    component.limpiarFiltros();
    component.setFiltro('marca', ev('Toyota'));
    expect(ids()).toEqual([1, 2]);
    component.setFiltro('modelo', ev('Hilux'));
    expect(ids()).toEqual([2]);
    component.limpiarFiltros();
    component.setFiltro('instalador', ev('10'));
    expect(ids()).toEqual([1]);
    component.limpiarFiltros();
    component.setFiltro('status', ev('cancelada'));
    expect(ids()).toEqual([3]);
    component.limpiarFiltros();
    component.setFiltro('cobro', ev('pagada'));
    expect(ids()).toEqual([2]);
  });

  it('filters the notes without a nota de venta', () => {
    create(rows());
    component.setFiltro('cobro', ev('sin_nota_venta'));
    expect(ids()).toEqual([3]);
  });

  it('resets the model when the brand changes and combines filters with the search', () => {
    create(rows());
    component.setFiltro('marca', ev('Toyota'));
    component.setFiltro('modelo', ev('Hilux'));
    component.setFiltro('marca', ev('Nissan'));
    expect(component.filtros.modelo).toBe('');
    component.limpiarFiltros();
    component.setFiltro('sucursal', ev('2'));
    component.filterDatatable(ev('ana'));
    expect(ids()).toEqual([2, 3]);
    component.setFiltro('status', ev('terminado'));
    expect(ids()).toEqual([2]);
  });

  it('works when the backend does not send the brand yet', () => {
    create([nota({ id: 1, car_brand_name: undefined }), nota({ id: 2, car_brand_name: undefined })]);
    expect(component.marcaOptions).toEqual([]);
    component.setFiltro('status', ev('en_proceso'));
    expect(ids()).toEqual([1, 2]);
  });

  it('distinguishes "no results with the filters" from "no data" and renders the card', () => {
    const fixture = TestBed.createComponent(NotasTrabajoListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    httpMock.expectOne(`${base}/notas-trabajo`).flush(rows());
    component.setFiltro('status', ev('terminado'));
    component.setFiltro('sucursal', ev('1'));
    fixture.detectChanges();
    const text: string = fixture.nativeElement.textContent;
    expect(text).toContain('No hay resultados con los filtros aplicados.');
    expect(text).not.toContain('No hay notas de trabajo para mostrar.');
    for (const label of ['Filtros', 'Sucursal', 'Marca', 'Modelo', 'Instalador', 'Estado', 'Cobro', 'Limpiar']) {
      expect(text).toContain(label);
    }
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

    component.nota = nota({ status: 'terminado', status_label: 'Terminado', is_close: true });
    expect(component.canEdit).toBe(false);
  });

  it('shows the badge of the nota de trabajo itself: En proceso, Terminado, Cancelada', () => {
    const component = TestBed.createComponent(NotaTrabajoViewComponent).componentInstance;
    component.ngOnInit();
    httpMock.expectOne(`${base}/notas-trabajo/3/`).flush(nota());

    expect(component.statusText).toBe('En proceso');
    expect(component.statusClass).toBe('status-progress');

    component.nota = nota({ status: 'terminado', status_label: 'Terminado', is_close: true });
    expect(component.statusText).toBe('Terminado');
    expect(component.statusClass).toBe('status-done');

    component.nota = nota({ status: 'cancelada', status_label: 'Cancelada', is_close: true });
    expect(component.statusClass).toBe('status-void');
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
    expect(element.querySelectorAll('.section-card').length).toBe(6); // 3 de datos + Cobro + 2 tablas
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

    component.nota = nota({ status: 'terminado', status_label: 'Terminado', is_close: true });
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
    const component = create(nota({ status: 'terminado', status_label: 'Terminado', is_close: true }));
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

describe('NotaTrabajoViewComponent - estados y acciones', () => {
  let httpMock: HttpTestingController;
  let component: NotaTrabajoViewComponent;
  const url = `${base}/notas-trabajo/3/`;
  const tick = () => new Promise<void>((resolve) => setTimeout(resolve));

  function setup(permissions: string[], data: AppNotaTrabajoDetail = nota()) {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [NotaTrabajoViewComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), routeWithId('3')],
    });
    httpMock = TestBed.inject(HttpTestingController);
    login(httpMock, permissions);
    component = TestBed.createComponent(NotaTrabajoViewComponent).componentInstance;
    component.ngOnInit();
    httpMock.expectOne(url).flush(data);
  }

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('terminar is offered with change_nota_trabajo and explains what is missing for a venta con instalacion', () => {
    setup(['product.change_nota_trabajo']);
    expect(component.canTerminar).toBe(true);
    expect(component.terminarBlockReason).toBe('Falta el código de garantía y el instalador.');

    component.nota = nota({ codigo_garantia: 'GAR-1' });
    expect(component.terminarBlockReason).toBe('Falta el instalador.');

    component.nota = nota({ codigo_garantia: 'GAR-1', instaladar: 2 });
    expect(component.terminarBlockReason).toBe('');
  });

  it('terminar does not ask for garantia / instalador in metro lineal', () => {
    setup(['product.change_nota_trabajo'], nota({ sales_type: 'venta_metro_lineal' }));
    expect(component.terminarBlockReason).toBe('');
  });

  it('una sucursal inactiva se ve pero no se edita ni se cambia de estado', () => {
    setup(['product.change_nota_trabajo', 'product.delete_nota_trabajo']);
    expect(component.canEdit).toBe(true);
    expect(component.canTerminar).toBe(true);
    expect(component.canAnular).toBe(true);

    component.nota = nota({ sucursal_activa: false });
    expect(component.sucursalInactiva).toBe(true);
    expect(component.canEdit).toBe(false);
    expect(component.canTerminar).toBe(false);
    expect(component.canCorregir).toBe(false);
    expect(component.canAnular).toBe(false);
  });

  it('terminar, corregir and anular follow permission and state', () => {
    setup([]);
    expect(component.canTerminar).toBe(false);
    expect(component.canCorregir).toBe(false);
    expect(component.canAnular).toBe(false);
  });

  it('corregir only when terminado with the nota de venta still por cobrar', () => {
    setup(['product.change_nota_trabajo']);
    component.nota = nota({ status: 'terminado', status_label: 'Terminado', is_close: true });
    expect(component.canCorregir).toBe(true);
    expect(component.canTerminar).toBe(false);
    component.nota = nota({
      status: 'terminado', status_label: 'Terminado', is_close: true,
      nota_venta: { id: 7, status: 'pagada', status_label: 'Pagada', total_price: '340.00' },
    });
    expect(component.canCorregir).toBe(false);
  });

  it('anular needs delete_nota_trabajo and the trabajo en proceso', () => {
    setup(['product.delete_nota_trabajo']);
    expect(component.canAnular).toBe(true);
    component.nota = nota({ status: 'terminado', status_label: 'Terminado', is_close: true });
    expect(component.canAnular).toBe(false);
  });

  it('terminar posts the action after confirming and shows the updated note', async () => {
    setup(['product.change_nota_trabajo'], nota({ codigo_garantia: 'GAR-1', instaladar: 2 }));
    spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: true } as SweetAlertResult));

    const pending = component.terminar();
    await tick();
    const req = httpMock.expectOne(`${url}terminar/`);
    expect(req.request.method).toBe('POST');
    req.flush(nota({ status: 'terminado', status_label: 'Terminado', is_close: true }));
    await pending;

    expect(component.nota?.status).toBe('terminado');
    expect(component.savedMessage).toContain('terminado');
  });

  it('corregir posts the action', async () => {
    setup(['product.change_nota_trabajo'], nota({ status: 'terminado', status_label: 'Terminado', is_close: true }));
    spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: true } as SweetAlertResult));

    const pending = component.corregir();
    await tick();
    httpMock.expectOne(`${url}corregir/`).flush(nota());
    await pending;

    expect(component.nota?.status).toBe('en_proceso');
  });

  it('anular posts the action and shows the cancelled note', async () => {
    setup(['product.delete_nota_trabajo']);
    spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: true } as SweetAlertResult));

    const pending = component.anular();
    await tick();
    httpMock.expectOne(`${url}anular/`).flush(nota({ status: 'cancelada', status_label: 'Cancelada', is_close: true }));
    await pending;

    expect(component.nota?.status).toBe('cancelada');
  });

  it('does nothing when the confirmation is cancelled', async () => {
    setup(['product.change_nota_trabajo'], nota({ codigo_garantia: 'GAR-1', instaladar: 2 }));
    spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: false } as SweetAlertResult));

    await component.terminar();

    httpMock.expectNone(`${url}terminar/`);
  });

  it('a server rejection shows an error alert and keeps the note', async () => {
    setup(['product.change_nota_trabajo'], nota({ codigo_garantia: 'GAR-1', instaladar: 2 }));
    const fire = spyOn(Swal, 'fire');
    fire.and.returnValue(Promise.resolve({ isConfirmed: true } as SweetAlertResult));

    const pending = component.terminar();
    await tick();
    httpMock.expectOne(`${url}terminar/`).flush({ detail: 'Debe agregar un Instalador' }, { status: 409, statusText: 'Conflict' });
    await pending;

    expect(component.nota?.status).toBe('en_proceso');
    expect(fire).toHaveBeenCalledTimes(2);
  });
});

describe('NotasTrabajoListComponent - estado y cobro', () => {
  it('maps the badge class of a nota status', () => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [NotasTrabajoListComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    const component = TestBed.createComponent(NotasTrabajoListComponent).componentInstance;
    expect(component.badge('en_proceso')).toBe('status-badge status-progress');
    expect(component.badge('terminado')).toBe('status-badge status-done');
    expect(component.badge('cancelada')).toBe('status-badge status-void');
    expect(component.badge('pagada')).toBe('status-badge status-final');
  });
});
