import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/service/auth.service';
import { AppNotaTrabajo, AppNotaTrabajoDetail } from '../ordenes.model';
import { NotaTrabajoEditComponent } from './nota-trabajo-edit.component';
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

  it('cannot edit without permission', () => {
    const component = TestBed.createComponent(NotaTrabajoViewComponent).componentInstance;
    component.ngOnInit();
    httpMock.expectOne(`${base}/notas-trabajo/3/`).flush(nota());
    expect(component.canEdit).toBe(false);
  });
});

describe('NotaTrabajoEditComponent', () => {
  let httpMock: HttpTestingController;
  let router: Router;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [NotaTrabajoEditComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), routeWithId('3')],
    });
    httpMock = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  function create(detail: AppNotaTrabajoDetail) {
    const component = TestBed.createComponent(NotaTrabajoEditComponent).componentInstance;
    component.ngOnInit();
    httpMock.expectOne(`${base}/notas-trabajo/3/`).flush(detail);
    return component;
  }

  it('preloads the operational fields and the installers of the sucursal', () => {
    const component = create(
      nota({ codigo_garantia: 'GAR-1', observaciones: 'ok', salida_vehiculo: '2026-09-30T15:30:00' })
    );
    httpMock
      .expectOne((r) => r.url === `${base}/catalogo/instaladores` && r.params.get('sucursal') === '1')
      .flush([{ id: 7, name: 'Pedro' }]);

    expect(component.form.value.codigo_garantia).toBe('GAR-1');
    expect(component.form.value.salida_vehiculo).toBe('2026-09-30T15:30');
    expect(component.instaladores.length).toBe(1);
  });

  it('sends only the operational fields', () => {
    const component = create(nota());
    httpMock.expectOne((r) => r.url === `${base}/catalogo/instaladores`).flush([{ id: 7, name: 'Pedro' }]);
    component.form.patchValue({ instaladar: 7, codigo_garantia: ' GAR-2 ', observaciones: 'listo' });

    component.save();

    const req = httpMock.expectOne(`${base}/notas-trabajo/3/`);
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({
      instaladar: 7, codigo_garantia: 'GAR-2', salida_vehiculo: null, observaciones: 'listo',
    });
    req.flush(nota());
    expect(router.navigate).toHaveBeenCalledWith(['/ordenes/notas-trabajo/view', 3]);
  });

  it('does not submit a garantia code longer than 12 characters', () => {
    const component = create(nota());
    httpMock.expectOne((r) => r.url === `${base}/catalogo/instaladores`).flush([]);
    component.form.patchValue({ codigo_garantia: 'X'.repeat(13) });

    component.save();

    httpMock.expectNone(`${base}/notas-trabajo/3/`);
  });

  it('shows the server error (e.g. duplicated garantia code)', () => {
    const component = create(nota());
    httpMock.expectOne((r) => r.url === `${base}/catalogo/instaladores`).flush([]);
    component.form.patchValue({ codigo_garantia: 'DUP' });

    component.save();
    httpMock
      .expectOne(`${base}/notas-trabajo/3/`)
      .flush({ codigo_garantia: ['ya existe'] }, { status: 400, statusText: 'Bad Request' });

    expect(component.errorMessage).toBe('ya existe');
  });

  it('redirects to the view when the note is already finalized', () => {
    create(nota({ is_finalizada: true }));
    expect(router.navigate).toHaveBeenCalledWith(['/ordenes/notas-trabajo/view', 3]);
  });
});
