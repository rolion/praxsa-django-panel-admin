import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, TestRequest, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import Swal, { SweetAlertResult } from 'sweetalert2';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/service/auth.service';
import { AppProforma } from '../../ordenes/ordenes.model';
import {
  ColaTaller,
  ConsumoLaminas,
  DashboardKpis,
  ItemsSolicitados,
  ProformasRecientes,
  ProformasVsVentas,
  StockCritico,
} from '../dashboard.model';
import { MainComponent } from './main.component';

const api = `${environment.apiUrl}/product`;
const base = { generado: '2026-09-30T10:15:00', sucursal: null };

const kpis = (overrides: Partial<DashboardKpis> = {}): DashboardKpis => ({
  ...base,
  ventas: { mes: '1500.00', mes_anterior: '1000.00', variacion: '50.0' },
  proformas_activas: { monto: '800.00', cantidad: 3 },
  conversion: { convertidas: 2, emitidas: 4, porcentaje: '50.0' },
  instalaciones: { en_taller: 2, terminadas_hoy: 1 },
  sin_sucursal: false,
  ...overrides,
});
const serie: ProformasVsVentas = { ...base, meses: ['2026-08', '2026-09'], cotizado: ['10.00', '20.00'], vendido: ['5.00', '8.00'] };
const consumo: ConsumoLaminas = { ...base, meses: ['2026-09'], series: [{ nombre: 'Ceramica', metros: ['3.00'], total: '3.00' }] };
const items: ItemsSolicitados = { ...base, total: 2, items: [{ nombre: 'Parabrisas', cantidad: 2 }] };
const stock = (filas: StockCritico['filas'] = []): StockCritico => ({
  ...base, contadores: { criticos: 1, bajos: 0, ok: 0 }, umbrales: { critico: '10.00', bajo: '30.00' }, filas,
});
const cola: ColaTaller = {
  ...base, total: 1,
  filas: [{
    nota_trabajo_id: 7, proforma_id: 4, cliente: 'Ana', modelo: 'Corolla', placa: 'ABC123', laminas: ['Ceramica'],
    status: 'en_proceso', status_label: 'En proceso', instalador: null, entrada_vehiculo: '2026-09-30T09:00:00',
  }],
};
const proforma = (overrides: Partial<AppProforma> = {}): AppProforma => ({
  id: 1, sales_type: 'venta_instalacion', sales_type_label: 'Venta con Instalación', name: 'Ana', sucursal: 1,
  sucursal_name: 'Central', car_model_name: 'Corolla', car_brand_name: 'Toyota', car_plate: 'ABC123',
  total_price: '340.00', discount: '0.00', total_a_pagar: '340.00', proforma_created_on: '2026-09-29T10:00:00',
  status: 'proforma', status_label: 'Proforma', is_close: false, nota_trabajo_id: null, ...overrides,
});
const recientes = (proformas: AppProforma[] = [proforma()]): ProformasRecientes => ({ ...base, proformas });
const payloads: Record<string, object> = {
  kpis: kpis(), 'proformas-vs-ventas': serie, 'consumo-laminas': consumo, 'items-solicitados': items,
  'stock-critico': stock(), 'cola-taller': cola, 'proformas-recientes': recientes(),
};

describe('MainComponent (dashboard)', () => {
  let fixture: ComponentFixture<MainComponent>;
  let component: MainComponent;
  let httpMock: HttpTestingController;
  let authService: AuthService;
  const tick = () => new Promise<void>((resolve) => setTimeout(resolve));

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [MainComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    httpMock = TestBed.inject(HttpTestingController);
    authService = TestBed.inject(AuthService);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  const req = (path: string): TestRequest => httpMock.expectOne((r) => r.url === `${api}/${path}`);

  function login(permissions: string[]): void {
    authService.login('u', 'p').subscribe();
    httpMock.expectOne(`${api}/api-panel-admin-token-auth/`).flush({
      token: 't', user_id: 1, username: 'u', name: 'U', lastname: 'U', is_staff: true, groups: [], permissions,
    });
  }

  /** Crea el componente y contesta los 8 pedidos iniciales (sucursales + 7 widgets). */
  function create(overrides: { kpis?: DashboardKpis; stock?: StockCritico; recientes?: ProformasRecientes; sucursales?: unknown[] } = {}) {
    fixture = TestBed.createComponent(MainComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    req('ordenes/catalogo/sucursales').flush(overrides.sucursales ?? [{ id: 1, name: 'Central', address: 'x' }]);
    req('dashboard/kpis').flush(overrides.kpis ?? kpis());
    req('dashboard/proformas-vs-ventas').flush(serie);
    req('dashboard/consumo-laminas').flush(consumo);
    req('dashboard/items-solicitados').flush(items);
    req('dashboard/stock-critico').flush(overrides.stock ?? stock());
    req('dashboard/cola-taller').flush(cola);
    req('dashboard/proformas-recientes').flush(overrides.recientes ?? recientes());
    fixture.detectChanges();
  }

  function expectAllReloaded(): void {
    Object.keys(payloads).forEach((name) => req(`dashboard/${name}`).flush(payloads[name]));
  }

  const text = () => (fixture.nativeElement as HTMLElement).textContent ?? '';

  it('loads every widget', () => {
    create();
    expect(component.kpis.data?.proformas_activas.cantidad).toBe(3);
    expect(component.cola.data?.filas.length).toBe(1);
    expect(component.lineOptions?.series.length).toBe(2);
    expect(text()).toContain('Proformas activas');
  });

  it('a failing widget does not block the others and can be retried on its own', () => {
    fixture = TestBed.createComponent(MainComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    req('ordenes/catalogo/sucursales').flush([]);
    req('dashboard/kpis').flush({ detail: 'boom' }, { status: 500, statusText: 'Server Error' });
    req('dashboard/proformas-vs-ventas').flush(serie);
    req('dashboard/consumo-laminas').flush(consumo);
    req('dashboard/items-solicitados').flush(items);
    req('dashboard/stock-critico').flush(stock());
    req('dashboard/cola-taller').flush(cola);
    req('dashboard/proformas-recientes').flush(recientes());
    fixture.detectChanges();

    expect(component.kpis.error).toBe('boom');
    expect(component.cola.data).not.toBeNull();
    expect(text()).toContain('Reintentar');

    component.loadKpis();
    req('dashboard/kpis').flush(kpis());
    expect(component.kpis.error).toBe('');
    expect(component.kpis.data).not.toBeNull();
  });

  it('hides the sales card when the server sends null (no permission)', () => {
    create({ kpis: kpis({ ventas: null }) });
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.dash-kpi-ventas')).toBeNull();
    expect(text()).not.toContain('Ventas del mes');
    expect(text()).toContain('Proformas activas');
  });

  it('shows the sales card with the variation when present', () => {
    create();
    expect((fixture.nativeElement as HTMLElement).querySelector('.dash-kpi-ventas')).not.toBeNull();
    expect(text()).toContain('+50.0 %');
    expect(text()).toContain('1500.00 Bs');
  });

  it('warns when the user has no sucursal', () => {
    create({ kpis: kpis({ sin_sucursal: true }) });
    expect(text()).toContain('no tiene una sucursal asignada');
  });

  it('offers the sucursal selector only with more than one sucursal', () => {
    create();
    expect(component.showSucursalSelector).toBe(false);
  });

  it('offers the selector with two sucursales and reloads everything with the choice', () => {
    create({ sucursales: [{ id: 1, name: 'A', address: '' }, { id: 2, name: 'B', address: '' }] });
    expect(component.showSucursalSelector).toBe(true);
    component.setSucursal(2);
    const kpisReq = req('dashboard/kpis');
    expect(kpisReq.request.params.get('sucursal')).toBe('2');
    kpisReq.flush(kpis());
    Object.keys(payloads)
      .filter((name) => name !== 'kpis')
      .forEach((name) => {
        const r = req(`dashboard/${name}`);
        expect(r.request.params.get('sucursal')).toBe('2');
        r.flush(payloads[name]);
      });
  });

  it('changing the period reloads only the three historical widgets', () => {
    create();
    component.setMeses(6);
    ['proformas-vs-ventas', 'consumo-laminas', 'items-solicitados'].forEach((name) => {
      const r = req(`dashboard/${name}`);
      expect(r.request.params.get('meses')).toBe('6');
      r.flush(payloads[name]);
    });
  });

  it('shows the empty states', () => {
    create();
    expect(text()).toContain('Sin alertas de stock');
  });

  it('shows the stock state with icon, text and color class', () => {
    create({
      stock: stock([{ sucursal_id: 1, sucursal: 'Central', lamina_id: 2, lamina: 'Ceramica', ancho: '1.50', metros: '4.00', rollos: 1, estado: 'critico' }]),
    });
    expect(text()).toContain('Crítico');
    expect(text()).toContain('4.00 m disponibles');
    expect((fixture.nativeElement as HTMLElement).querySelector('.dash-stock-row.stock-critico')).not.toBeNull();
    expect(component.stockPercent(component.stock.data!.filas[0], '30.00')).toBeCloseTo(13.33, 1);
  });

  it('shows "No asignado" when the work order has no installer', () => {
    create();
    expect(text()).toContain('No asignado');
  });

  it('shows "Convertir a venta" only for proformas with permission', () => {
    login(['product.add_nota_trabajo']);
    create({ recientes: recientes([proforma({ id: 1 }), proforma({ id: 2, status: 'en_trabajo', status_label: 'En trabajo' })]) });
    expect(component.canConvert(proforma())).toBe(true);
    expect(component.canConvert(proforma({ status: 'en_trabajo' }))).toBe(false);
    expect((fixture.nativeElement as HTMLElement).querySelectorAll('.dash-convert').length).toBe(1);
  });

  it('does not offer the conversion without the add_nota_trabajo permission', () => {
    create();
    expect(component.canConvert(proforma())).toBe(false);
    expect((fixture.nativeElement as HTMLElement).querySelector('.dash-convert')).toBeNull();
  });

  it('converts after confirming and reloads the whole dashboard', async () => {
    spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: true } as SweetAlertResult));
    login(['product.add_nota_trabajo']);
    create();

    const pending = component.convertir(proforma());
    await tick();
    const post = httpMock.expectOne(`${api}/ordenes/proformas/1/generar-nota-trabajo/`);
    expect(post.request.method).toBe('POST');
    expect(component.converting).toBe(1);
    post.flush({});
    await pending;

    expect(component.converting).toBeNull();
    expectAllReloaded();
  });

  it('does nothing when the confirmation is cancelled', async () => {
    spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: false } as SweetAlertResult));
    create();

    await component.convertir(proforma());

    httpMock.expectNone(`${api}/ordenes/proformas/1/generar-nota-trabajo/`);
    expect(component.converting).toBeNull();
  });

  it('shows the server message when the conversion fails and does not reload', async () => {
    const fire = spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: true } as SweetAlertResult));
    create();

    const pending = component.convertir(proforma());
    await tick();
    httpMock
      .expectOne(`${api}/ordenes/proformas/1/generar-nota-trabajo/`)
      .flush({ detail: 'no hay lamina disponible' }, { status: 409, statusText: 'Conflict' });
    await pending;

    expect(fire).toHaveBeenCalledWith(
      jasmine.objectContaining({ title: 'No se pudo aprobar la proforma', text: 'no hay lamina disponible' })
    );
    expect(component.converting).toBeNull();
  });
});
