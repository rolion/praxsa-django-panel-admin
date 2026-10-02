import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { NgbActiveModal, NgbModal } from '@ng-bootstrap/ng-bootstrap';
import Swal, { SweetAlertResult } from 'sweetalert2';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/service/auth.service';
import { AppNotaVenta, AppNotaVentaDetail } from '../ordenes.model';
import { NotaVentaViewComponent } from './nota-venta-view.component';
import { NotasVentaListComponent } from './notas-venta-list.component';
import { PagoModalComponent } from './pago-modal.component';
import { anularBlockReason, payBlockReason } from './nota-venta-rules';

const base = `${environment.apiUrl}/product/ordenes`;
const ev = (value: string) => ({ target: { value } }) as unknown as Event;
const tick = () => new Promise<void>((resolve) => setTimeout(resolve));

const venta = (overrides: Partial<AppNotaVentaDetail> = {}): AppNotaVentaDetail => ({
  id: 7, nota_trabajo_id: 3, proforma_id: 5, name: 'Ana', ci_nit: '123', total_price: '340.00',
  created_on: '2026-09-29T10:00:00', status: 'por_cobrar', status_label: 'Por cobrar',
  work_status: 'terminado', work_status_label: 'Terminado', sucursal_id: 1, sucursal_name: 'Central',
  pago: null, car_plate: 'ABC123', sales_type_label: 'Venta con Instalación', ...overrides,
});

function login(httpMock: HttpTestingController, permissions: string[]): void {
  TestBed.inject(AuthService).login('u', 'p').subscribe();
  httpMock.expectOne(`${environment.apiUrl}/product/api-panel-admin-token-auth/`).flush({
    token: 't', user_id: 1, username: 'u', name: 'U', lastname: 'U', is_staff: true, groups: [], permissions,
  });
}

describe('reglas de nota de venta', () => {
  it('pagar solo con el trabajo terminado', () => {
    expect(payBlockReason({ work_status: 'terminado' })).toBe('');
    expect(payBlockReason({ work_status: 'en_proceso' })).toBe('El trabajo aún no está terminado.');
  });

  it('anular no se permite con el trabajo terminado', () => {
    expect(anularBlockReason({ work_status: 'en_proceso' })).toBe('');
    expect(anularBlockReason({ work_status: 'terminado' })).toContain('corrija el trabajo');
  });
});

describe('NotasVentaListComponent', () => {
  let httpMock: HttpTestingController;
  let component: NotasVentaListComponent;
  let modal: jasmine.SpyObj<NgbModal>;

  beforeEach(() => {
    localStorage.clear();
    modal = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
    TestBed.configureTestingModule({
      imports: [NotasVentaListComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), { provide: NgbModal, useValue: modal }],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  function create(rows: AppNotaVenta[], permissions: string[] = []) {
    if (permissions.length) {
      login(httpMock, permissions);
    }
    const fixture = TestBed.createComponent(NotasVentaListComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    httpMock.expectOne(`${base}/notas-venta`).flush(rows);
    return fixture;
  }

  it('loads the rows and filters client side by number, proforma, client and CI/NIT', () => {
    create([venta(), venta({ id: 8, proforma_id: 6, name: 'Luis', ci_nit: '999' })]);
    expect(component.rows.length).toBe(2);
    component.filterDatatable({ target: { value: 'luis' } } as unknown as Event);
    expect(component.rows.map((r) => r.id)).toEqual([8]);
    component.filterDatatable({ target: { value: '123' } } as unknown as Event);
    expect(component.rows.map((r) => r.id)).toEqual([7]);
  });

  it('derives the action permissions', () => {
    create([venta()], ['product.add_pago', 'product.delete_nota_venta']);
    expect(component.canPay).toBe(true);
    expect(component.canAnular).toBe(true);
  });

  it('has no cobro permissions without them', () => {
    create([venta()]);
    expect(component.canPay).toBe(false);
    expect(component.canAnular).toBe(false);
  });

  it('shows the missing sucursal state when empty and the user has none', () => {
    component = TestBed.createComponent(NotasVentaListComponent).componentInstance;
    component.ngOnInit();
    httpMock.expectOne(`${base}/notas-venta`).flush([]);
    httpMock.expectOne(`${base}/catalogo/sucursales`).flush([]);
    expect(component.withoutSucursal).toBe(true);
  });

  it('opens the payment modal with the nota de venta and reloads on success', async () => {
    create([venta()]);
    const instance: Partial<PagoModalComponent> = {};
    modal.open.and.returnValue({ componentInstance: instance, result: Promise.resolve(venta()) } as never);

    component.pay(venta());
    await tick();

    expect(instance.notaVentaId).toBe(7);
    expect(instance.total).toBe('340.00');
    httpMock.expectOne(`${base}/notas-venta`).flush([venta({ status: 'pagada', status_label: 'Pagada' })]);
    expect(component.rows[0].status).toBe('pagada');
  });

  it('does not open the payment modal while the work is not finished', () => {
    create([venta({ work_status: 'en_proceso' })]);
    component.pay(venta({ work_status: 'en_proceso' }));
    expect(modal.open).not.toHaveBeenCalled();
  });

  it('a dismissed modal does not reload the list', async () => {
    create([venta()]);
    modal.open.and.returnValue({ componentInstance: {}, result: Promise.reject('cancel') } as never);
    component.pay(venta());
    await tick();
    httpMock.expectNone(`${base}/notas-venta`);
  });

  it('anula after confirming and reloads; it is blocked with the work finished', async () => {
    create([venta({ work_status: 'en_proceso' })]);
    spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: true } as SweetAlertResult));

    const pending = component.anular(venta({ work_status: 'en_proceso' }));
    await tick();
    const req = httpMock.expectOne(`${base}/notas-venta/7/anular/`);
    expect(req.request.method).toBe('POST');
    req.flush({});
    httpMock.expectOne(`${base}/notas-venta`).flush([]);
    httpMock.expectOne(`${base}/catalogo/sucursales`).flush([{ id: 1, name: 'Central', address: 'x' }]);
    await pending;

    await component.anular(venta({ work_status: 'terminado' }));
    httpMock.expectNone(`${base}/notas-venta/7/anular/`);
  });

  describe('filtros', () => {
    const rows = () => [
      venta({ id: 1, sucursal_id: 1, sucursal_name: 'Central', created_on: '2026-09-01T09:00:00', work_status: 'en_proceso', status: 'por_cobrar' }),
      venta({ id: 2, sucursal_id: 2, sucursal_name: 'Norte', created_on: '2026-09-15T09:00:00', work_status: 'terminado', status: 'pagada' }),
      venta({ id: 3, sucursal_id: 2, sucursal_name: 'Norte', created_on: null, work_status: 'terminado', status: 'anulada' }),
    ];
    const ids = () => component.rows.map((r) => r.id);

    it('offers the sucursales present in the loaded rows', () => {
      create(rows());
      expect(component.sucursalOptions.map((o) => o.label)).toEqual(['Central', 'Norte']);
    });

    it('filters by sucursal, trabajo and cobro', () => {
      create(rows());
      component.setFiltro('sucursal', ev('2'));
      expect(ids()).toEqual([2, 3]);
      component.limpiarFiltros();
      component.setFiltro('trabajo', ev('en_proceso'));
      expect(ids()).toEqual([1]);
      component.limpiarFiltros();
      component.setFiltro('cobro', ev('pagada'));
      expect(ids()).toEqual([2]);
    });

    it('filters by date range and excludes null dates while a range is active', () => {
      create(rows());
      expect(ids()).toEqual([1, 2, 3]);
      component.setFiltro('desde', ev('2026-09-10'));
      expect(ids()).toEqual([2]);
      component.setFiltro('hasta', ev('2026-09-15'));
      expect(ids()).toEqual([2]);
      component.limpiarFiltros();
      expect(ids()).toEqual([1, 2, 3]);
    });

    it('reports desde > hasta and does not filter by date', () => {
      create(rows());
      component.setFiltro('desde', ev('2026-10-01'));
      component.setFiltro('hasta', ev('2026-09-01'));
      expect(component.rangoError).toContain('inicial');
      expect(ids()).toEqual([1, 2, 3]);
    });

    it('combines filters with the search (AND)', () => {
      create(rows());
      component.filterDatatable(ev('norte'));
      expect(ids()).toEqual([2, 3]);
      component.setFiltro('cobro', ev('anulada'));
      expect(ids()).toEqual([3]);
    });

    it('distinguishes "no results with the filters" from "no data" and renders the card', () => {
      const fixture = TestBed.createComponent(NotasVentaListComponent);
      component = fixture.componentInstance;
      fixture.detectChanges();
      httpMock.expectOne(`${base}/notas-venta`).flush(rows());
      component.setFiltro('cobro', ev('pagada'));
      component.setFiltro('trabajo', ev('en_proceso'));
      fixture.detectChanges();
      const text: string = fixture.nativeElement.textContent;
      expect(text).toContain('No hay resultados con los filtros aplicados.');
      for (const label of ['Filtros', 'Sucursal', 'Desde', 'Hasta', 'Trabajo', 'Cobro', 'Limpiar']) {
        expect(text).toContain(label);
      }
    });
  });
});

describe('NotaVentaViewComponent', () => {
  let httpMock: HttpTestingController;
  let component: NotaVentaViewComponent;
  let modal: jasmine.SpyObj<NgbModal>;
  const url = `${base}/notas-venta/7/`;

  beforeEach(() => {
    localStorage.clear();
    modal = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
    TestBed.configureTestingModule({
      imports: [NotaVentaViewComponent],
      providers: [
        provideHttpClient(), provideHttpClientTesting(), provideRouter([]),
        { provide: NgbModal, useValue: modal },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: '7' }) } } },
      ],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  function create(data: AppNotaVentaDetail, permissions: string[] = []) {
    if (permissions.length) {
      login(httpMock, permissions);
    }
    const fixture = TestBed.createComponent(NotaVentaViewComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    httpMock.expectOne(url).flush(data);
    return fixture;
  }

  it('loads the nota de venta and renders the payment block', () => {
    const fixture = create(venta({
      status: 'pagada', status_label: 'Pagada',
      pago: { id: 1, monto: '340.00', tipo_pago: 'trans', tipo_pago_label: 'Tarjeta/QR', registro_contable: '1234/26', created_on: '2026-09-29T11:00:00', cerrado: false },
    }));
    fixture.detectChanges();
    httpMock.match(url).forEach((req) => req.flush(component.nota));
    const html: string = fixture.nativeElement.textContent;
    expect(html).toContain('Tarjeta/QR');
    expect(html).toContain('1234/26');
    expect(html).toContain('Pagada');
  });

  it('shows an error when it cannot be loaded (e.g. out of scope)', () => {
    component = TestBed.createComponent(NotaVentaViewComponent).componentInstance;
    component.ngOnInit();
    httpMock.expectOne(url).flush({}, { status: 404, statusText: 'Not Found' });
    expect(component.errorMessage).toContain('No se pudo cargar');
  });

  it('registrar pago needs add_pago and a por cobrar note; it is blocked until the work is finished', () => {
    create(venta({ work_status: 'en_proceso', work_status_label: 'En proceso' }), ['product.add_pago']);
    expect(component.canPay).toBe(true);
    expect(component.payBlockReason).toBe('El trabajo aún no está terminado.');

    component.nota = venta();
    expect(component.payBlockReason).toBe('');

    component.nota = venta({ status: 'pagada', status_label: 'Pagada' });
    expect(component.canPay).toBe(false);
  });

  it('una sucursal inactiva se ve pero no se cobra ni se anula', () => {
    create(venta(), ['product.add_pago', 'product.delete_nota_venta']);
    expect(component.canPay).toBe(true);
    expect(component.canAnular).toBe(true);

    component.nota = venta({ sucursal_activa: false });
    expect(component.sucursalInactiva).toBe(true);
    expect(component.canPay).toBe(false);
    expect(component.canAnular).toBe(false);
  });

  it('hides the cobro actions without permissions', () => {
    create(venta());
    expect(component.canPay).toBe(false);
    expect(component.canAnular).toBe(false);
    expect(component.canAnularPago).toBe(false);
  });

  it('anular pago only with delete_pago, a pagada note and an open account', () => {
    const pago = { id: 1, monto: '340.00', tipo_pago: 'efec' as const, tipo_pago_label: 'Efectivo', registro_contable: null, created_on: '2026-09-29T11:00:00', cerrado: false };
    create(venta({ status: 'pagada', status_label: 'Pagada', pago }), ['product.delete_pago']);
    expect(component.canAnularPago).toBe(true);
    component.nota = venta({ status: 'pagada', status_label: 'Pagada', pago: { ...pago, cerrado: true } });
    expect(component.canAnularPago).toBe(false);
  });

  it('opens the payment modal and shows the updated note with a message', async () => {
    create(venta(), ['product.add_pago']);
    const instance: Partial<PagoModalComponent> = {};
    const updated = venta({ status: 'pagada', status_label: 'Pagada' });
    modal.open.and.returnValue({ componentInstance: instance, result: Promise.resolve(updated) } as never);

    component.pay();
    await tick();

    expect(instance.notaVentaId).toBe(7);
    expect(component.nota?.status).toBe('pagada');
    expect(component.savedMessage).toBe('Pago registrado.');
  });

  it('does not open the modal while the work is not finished', () => {
    create(venta({ work_status: 'en_proceso' }), ['product.add_pago']);
    component.pay();
    expect(modal.open).not.toHaveBeenCalled();
  });

  it('anular pago posts the action after confirming', async () => {
    const pago = { id: 1, monto: '340.00', tipo_pago: 'efec' as const, tipo_pago_label: 'Efectivo', registro_contable: null, created_on: '2026-09-29T11:00:00', cerrado: false };
    create(venta({ status: 'pagada', status_label: 'Pagada', pago }), ['product.delete_pago']);
    spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: true } as SweetAlertResult));

    const pending = component.anularPago();
    await tick();
    const req = httpMock.expectOne(`${url}anular-pago/`);
    expect(req.request.method).toBe('POST');
    req.flush(venta());
    await pending;

    expect(component.nota?.status).toBe('por_cobrar');
    expect(component.savedMessage).toBe('Pago anulado.');
  });

  it('anular nota de venta posts the action after confirming', async () => {
    create(venta({ work_status: 'en_proceso', work_status_label: 'En proceso' }), ['product.delete_nota_venta']);
    spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: true } as SweetAlertResult));

    const pending = component.anular();
    await tick();
    httpMock.expectOne(`${url}anular/`).flush(venta({ status: 'anulada', status_label: 'Anulada', work_status: 'cancelada', work_status_label: 'Cancelada' }));
    await pending;

    expect(component.nota?.status).toBe('anulada');
  });

  it('anular nota de venta is blocked with the work finished', async () => {
    create(venta(), ['product.delete_nota_venta']);
    expect(component.anularBlockReason).toContain('corrija el trabajo');
    await component.anular();
    httpMock.expectNone(`${url}anular/`);
  });
});

describe('PagoModalComponent', () => {
  let httpMock: HttpTestingController;
  let component: PagoModalComponent;
  let activeModal: jasmine.SpyObj<NgbActiveModal>;

  beforeEach(() => {
    activeModal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [PagoModalComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), { provide: NgbActiveModal, useValue: activeModal }],
    });
    httpMock = TestBed.inject(HttpTestingController);
    component = TestBed.createComponent(PagoModalComponent).componentInstance;
    component.notaVentaId = 7;
    component.total = '340.00';
  });

  afterEach(() => httpMock.verify());

  it('sends the tipo de pago and registro contable, never a monto, and closes with the updated note', async () => {
    spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: true } as SweetAlertResult));
    component.form.patchValue({ tipo_pago: 'trans', registro_contable: '1234/26' });

    const pending = component.submit();
    await tick();
    const req = httpMock.expectOne(`${base}/notas-venta/7/pago/`);
    expect(req.request.body).toEqual({ tipo_pago: 'trans', registro_contable: '1234/26' });
    req.flush(venta({ status: 'pagada', status_label: 'Pagada' }));
    await pending;

    expect(activeModal.close).toHaveBeenCalled();
  });

  it('rejects a malformed registro contable without calling the server', async () => {
    component.form.patchValue({ registro_contable: 'abc' });
    await component.submit();
    expect(component.submitted).toBe(true);
    httpMock.expectNone(`${base}/notas-venta/7/pago/`);
  });

  it('the registro contable is optional', async () => {
    spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: true } as SweetAlertResult));
    const pending = component.submit();
    await tick();
    const req = httpMock.expectOne(`${base}/notas-venta/7/pago/`);
    expect(req.request.body).toEqual({ tipo_pago: 'efec', registro_contable: '' });
    req.flush(venta());
    await pending;
  });

  it('does not call the server when the confirmation is cancelled', async () => {
    spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: false } as SweetAlertResult));
    await component.submit();
    httpMock.expectNone(`${base}/notas-venta/7/pago/`);
    expect(activeModal.close).not.toHaveBeenCalled();
  });

  it('shows the server error and keeps the modal open', async () => {
    spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: true } as SweetAlertResult));
    const pending = component.submit();
    await tick();
    httpMock.expectOne(`${base}/notas-venta/7/pago/`).flush({ detail: 'El trabajo aún no está terminado; no se puede registrar el pago.' }, { status: 409, statusText: 'Conflict' });
    await pending;

    expect(component.errorMessage).toContain('El trabajo aún no está terminado');
    expect(component.saving).toBe(false);
    expect(activeModal.close).not.toHaveBeenCalled();
  });
});
