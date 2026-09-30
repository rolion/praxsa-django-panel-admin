import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { BehaviorSubject } from 'rxjs';
import { AuthService } from '@core';
import { User } from '../core/models/user';
import { environment } from '../../environments/environment';
import { AccesoModalService } from '../cliente/acceso-modal.service';
import { CalculadoraComponent } from './calculadora.component';

const base = `${environment.apiUrl}/product`;

const catalog = {
  sucursales: [{ id: 1, name: 'Central', addres: 'x' }],
  brands: [{ id: 1, name: 'Toyota' }, { id: 2, name: 'Kia' }],
  models: [
    { id: 9, name: 'Hilux', brand_id: 1, image: 'https://api.test/media/car_models/hilux.png' },
    { id: 10, name: 'Rio', brand_id: 2, image: null },
  ],
};
const modelParts = {
  car_parts: [
    { id: 1, width: '1.50', length: '1.20', quantity: 2, model_id: 9, part_id: 5, part_name: 'Parabrisas', installation_price: 50 },
    { id: 2, width: '0.90', length: '1.00', quantity: 1, model_id: 9, part_id: 6, part_name: 'Puerta delantera izquierda', installation_price: 20 },
  ],
};
const inventory = {
  inventario: [
    { bobina_film_id: 3, bobina_film_name: 'Carbon', bobina_width: '1.50', bobina_metros_disponibles: 50, bobina_price: 120, bobina_id: 3 },
    { bobina_film_id: 4, bobina_film_name: 'Basica', bobina_width: '1.00', bobina_metros_disponibles: 10, bobina_price: 90, bobina_id: 4 },
  ],
};
const profile = { name: 'Ana', lastname: 'Gomez', email: 'ana@test.com', phone_number: '70000001', car_plate: 'ABC123', ci_nit: '' };

interface AuthServiceTestAccess {
  currentUserSubject: BehaviorSubject<User>;
}

describe('CalculadoraComponent', () => {
  let fixture: ComponentFixture<CalculadoraComponent>;
  let component: CalculadoraComponent;
  let httpMock: HttpTestingController;
  let router: Router;
  let auth: AuthService;
  let acceso: { open: jasmine.Spy };
  let toastr: { success: jasmine.Spy };
  let staffCanCreate = true;

  const setSession = (user: User) => (auth as unknown as AuthServiceTestAccess).currentUserSubject.next(user);
  const CLIENT = { token: 't', isStaff: false } as User;
  const STAFF = { token: 't', isStaff: true } as User;

  function setup(options: { session?: User; sucursales?: unknown[]; query?: Record<string, string> } = {}) {
    localStorage.clear();
    acceso = { open: jasmine.createSpy('open').and.resolveTo(false) };
    toastr = { success: jasmine.createSpy('success') };
    TestBed.configureTestingModule({
      imports: [CalculadoraComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: AccesoModalService, useValue: acceso },
        { provide: ToastrService, useValue: toastr },
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(options.query ?? {}) } } },
      ],
    });
    httpMock = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    auth = TestBed.inject(AuthService);
    spyOn(auth, 'hasPermission').and.callFake(() => staffCanCreate);
    if (options.session) {
      setSession(options.session);
    }
    fixture = TestBed.createComponent(CalculadoraComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    if (options.session === CLIENT) {
      httpMock.expectOne(`${base}/client/me`).flush(profile);
    }
    httpMock.expectOne(`${base}/calculator_info`).flush({ ...catalog, sucursales: options.sucursales ?? catalog.sucursales });
    fixture.detectChanges();
  }

  function pickModel(parts: object = modelParts, inv: object = inventory, brand = 1, model = 9) {
    component.filters.get('brand')?.setValue(brand);
    component.onBrandChange();
    component.filters.get('model')?.setValue(model);
    component.onModelChange();
    fixture.detectChanges();
    httpMock.expectOne(`${base}/model_parts/${model}`).flush(parts);
    httpMock.expectOne(`${base}/get_inventory/1/0/0`).flush(inv);
    fixture.detectChanges();
  }

  /** Cotiza Parabrisas (Carbon) y Puerta (Basica): 388 + 110 = 498. */
  function quoteTwoItems() {
    component.line(0).get('reel')?.setValue('3|1.50');
    component.line(1).get('reel')?.setValue('4|1.00');
  }

  const text = () => (fixture.nativeElement as HTMLElement).textContent ?? '';
  const total = () => (fixture.nativeElement as HTMLElement).querySelector('[data-testid="total"]')?.textContent?.trim();

  beforeEach(() => {
    staffCanCreate = true;
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  describe('catalogo publico y cotizacion', () => {
    it('loads the catalog from the public endpoints without a session (no client/me call)', () => {
      setup();
      expect(component.catalogsLoaded()).toBeTrue();
      expect(component.sucursales()[0]).toEqual({ id: 1, name: 'Central', address: 'x' });
      expect(component.brands().length).toBe(2);
    });

    it('starts in the initial state with step 1 and disabled actions', () => {
      setup();
      expect(component.state()).toBe('initial');
      expect(component.step()).toBe(1);
      expect(text()).toContain('Selecciona sucursal, marca y modelo');
      expect(total()).toBe('Bs 0');
      expect(component.canAct).toBeFalse();
    });

    it('fixes the only sucursal (read only)', () => {
      setup();
      expect(component.filters.getRawValue().sucursal).toBe(1);
      expect(component.filters.get('sucursal')?.disabled).toBeTrue();
    });

    it('warns when there is no sucursal', () => {
      setup({ sucursales: [] });
      expect(text()).toContain('Asigne una sucursal');
    });

    it('filters models by brand in memory (no extra request) and enables the model select', () => {
      setup();
      expect(component.filters.get('model')?.disabled).toBeTrue();
      component.filters.get('brand')?.setValue(2);
      component.onBrandChange();
      expect(component.models().map((m) => m.name)).toEqual(['Rio']);
      expect(component.filters.get('model')?.enabled).toBeTrue();
    });

    it('shows skeletons while loading and then the active table at step 2', () => {
      setup();
      component.filters.get('brand')?.setValue(1);
      component.onBrandChange();
      component.filters.get('model')?.setValue(9);
      component.onModelChange();
      fixture.detectChanges();
      expect(component.state()).toBe('loading');
      expect((fixture.nativeElement as HTMLElement).querySelector('[data-state="loading"]')).not.toBeNull();
      httpMock.expectOne(`${base}/model_parts/9`).flush(modelParts);
      httpMock.expectOne(`${base}/get_inventory/1/0/0`).flush(inventory);
      fixture.detectChanges();
      expect(component.state()).toBe('active');
      expect(component.step()).toBe(2);
      expect(text()).toContain('1.50 × 1.20 m · Cantidad 2');
    });

    it('normalizes the public responses and shows the model image', () => {
      setup();
      pickModel();
      expect(component.items()[0]).toEqual({
        id: 1, car_part_id: 5, car_part_name: 'Parabrisas', width: '1.50', length: '1.20', quantity: 2, installation_price: '50.00',
      });
      expect(component.reels()[0]).toEqual({
        window_film: 3, window_film_name: 'Carbon', width: '1.50', available_meters: '50.00', unit_price: '120.00',
      });
      const img = (fixture.nativeElement as HTMLElement).querySelector('.calc-summary-image img');
      expect(img?.getAttribute('src')).toBe('https://api.test/media/car_models/hilux.png');
    });

    it('only offers films wide enough and with stock, cheapest first', () => {
      setup();
      pickModel();
      expect(component.optionsByItem()[0].map((o) => o.name)).toEqual(['Carbon']);
      expect(component.optionsByItem()[1].map((o) => o.name)).toEqual(['Basica', 'Carbon']);
    });

    it('recalculates the subtotals and the total when a film is chosen or changed', () => {
      setup();
      pickModel();
      quoteTwoItems();
      fixture.detectChanges();
      expect(component.quote().lines.map((l) => l.subtotal)).toEqual([388, 110]);
      expect(component.quote().total).toBe(498);
      expect(total()).toBe('Bs 498');
      component.line(1).get('reel')?.setValue('3|1.50');
      expect(component.quote().total).toBe(528);
    });

    it('excludes an item from the total and restores it', () => {
      setup();
      pickModel();
      quoteTwoItems();
      component.toggleExcluded(0);
      expect(component.quote().total).toBe(110);
      expect(component.line(0).get('reel')?.disabled).toBeTrue();
      component.toggleExcluded(0);
      expect(component.quote().total).toBe(498);
      expect(component.line(0).get('reel')?.enabled).toBeTrue();
    });

    it('shows the empty state when the model has no items or the sucursal has no reels', () => {
      setup();
      pickModel({ car_parts: [] }, inventory);
      expect(component.state()).toBe('empty');
      expect(text()).toContain('no tiene ítems configurados');
    });

    it('shows the empty state for a sucursal without stock', () => {
      setup();
      pickModel(modelParts, { inventario: [] });
      expect(component.state()).toBe('empty');
      expect(text()).toContain('No hay láminas con stock');
    });

    it('warns on a row when no reel fits the item', () => {
      setup();
      pickModel(modelParts, { inventario: [inventory.inventario[1]] });
      expect(component.noOptionsWarning(0)).toContain('mínimo 1.50 m');
      expect(component.noOptionsWarning(1)).toBeNull();
    });

    it('shows the error state and retries the load', () => {
      setup();
      component.filters.get('brand')?.setValue(1);
      component.onBrandChange();
      component.filters.get('model')?.setValue(9);
      component.onModelChange();
      httpMock.expectOne(`${base}/model_parts/9`).flush('x', { status: 500, statusText: 'err' });
      httpMock.match(`${base}/get_inventory/1/0/0`); // forkJoin cancela la otra peticion
      fixture.detectChanges();
      expect(component.state()).toBe('error');
      component.retry();
      httpMock.expectOne(`${base}/model_parts/9`).flush(modelParts);
      httpMock.expectOne(`${base}/get_inventory/1/0/0`).flush(inventory);
      expect(component.state()).toBe('active');
    });

    it('shows an error when the catalog cannot be loaded', () => {
      TestBed.configureTestingModule({
        imports: [CalculadoraComponent],
        providers: [
          provideHttpClient(), provideHttpClientTesting(), provideRouter([]),
          { provide: AccesoModalService, useValue: { open: () => Promise.resolve(false) } },
          { provide: ToastrService, useValue: { success: () => undefined } },
          { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap({}) } } },
        ],
      });
      httpMock = TestBed.inject(HttpTestingController);
      fixture = TestBed.createComponent(CalculadoraComponent);
      fixture.detectChanges();
      httpMock.expectOne(`${base}/calculator_info`).flush('x', { status: 500, statusText: 'err' });
      fixture.detectChanges();
      expect(fixture.componentInstance.state()).toBe('error');
      expect(text()).toContain('No se pudieron cargar sucursales y marcas');
    });

    it('builds a wa.me link with the vehicle, priced items and total', () => {
      setup();
      pickModel();
      component.line(0).get('reel')?.setValue('3|1.50');
      const url = decodeURIComponent(component.whatsappUrl);
      expect(component.whatsappUrl.startsWith('https://wa.me/59178181012?text=')).toBeTrue();
      expect(url).toContain('Vehiculo: Toyota Hilux');
      expect(url).toContain('Parabrisas: Carbon (Bs 388)');
      expect(url).toContain('Total referencial: Bs 388');
    });
  });

  describe('crear proforma sin sesion', () => {
    it('shows "Crear Proforma" to anonymous visitors and asks to sign in; nothing is saved if the modal is dismissed', async () => {
      setup();
      pickModel();
      component.line(0).get('reel')?.setValue('3|1.50');
      fixture.detectChanges();
      expect(text()).toContain('Crear Proforma');

      component.createProforma();
      await fixture.whenStable();

      expect(acceso.open).toHaveBeenCalledWith('login', jasmine.stringContaining('guardar tu proforma'));
      expect(component.creating()).toBeFalse();
      expect(router.navigate).not.toHaveBeenCalled();
      httpMock.expectNone(`${base}/invoice`);
      // La cotizacion se conserva intacta.
      expect(component.quote().total).toBe(388);
    });

    it('after logging in through the modal it saves the proforma with the account data', async () => {
      setup();
      pickModel();
      quoteTwoItems();
      acceso.open.and.callFake(() => {
        setSession(CLIENT);
        return Promise.resolve(true);
      });

      component.createProforma();
      await fixture.whenStable();

      // Refresco del perfil por el cambio de sesion + lectura del guardado.
      httpMock.match(`${base}/client/me`).forEach((r) => r.flush(profile));
      const req = httpMock.expectOne(`${base}/invoice`);
      req.flush({ id: 41 });
      expect(router.navigate).toHaveBeenCalledWith(['/mis-proformas'], { state: { savedId: 41 } });
    });
  });

  describe('crear proforma como cliente', () => {
    it('loads the profile, shows "A nombre de" and hides nothing', () => {
      setup({ session: CLIENT });
      pickModel();
      expect(component.profile()).toEqual(profile);
      expect(text()).toContain('A nombre de');
      expect(text()).toContain('ABC123');
      expect(text()).toContain('Crear Proforma');
    });

    it('saves with POST invoice using the account data and goes to "Mis proformas" with a toast', async () => {
      setup({ session: CLIENT });
      pickModel();
      quoteTwoItems();
      component.toggleExcluded(1); // solo el parabrisas

      component.createProforma();
      expect(component.saving()).toBeTrue();
      expect(component.step()).toBe(3);
      httpMock.expectOne(`${base}/client/me`).flush(profile);
      const req = httpMock.expectOne(`${base}/invoice`);

      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({
        name: 'Ana Gomez',
        email: 'ana@test.com',
        car_plate: 'ABC123',
        car_model_id: 9,
        total_price: '388.00',
        phone_number: '70000001',
        ci_nit: null,
        sucursal: 1,
        carPartItems: [
          {
            car_part: 5, width: '1.50', length: '1.20', quantity: 2, window_film: 3,
            installation_price: '50.00', window_film_price: '120.00', sub_total: '388.00',
          },
        ],
      });
      req.flush({ id: 41 });

      expect(component.saving()).toBeFalse();
      expect(toastr.success).toHaveBeenCalledWith('Proforma 41 guardada');
      expect(router.navigate).toHaveBeenCalledWith(['/mis-proformas'], { state: { savedId: 41 } });
      expect(acceso.open).not.toHaveBeenCalled();
    });

    it('sends the account ci_nit when it exists', () => {
      setup({ session: CLIENT });
      pickModel();
      component.line(0).get('reel')?.setValue('3|1.50');
      expect(component.buildInvoice({ ...profile, ci_nit: '123456' })?.ci_nit).toBe('123456');
    });

    it('does not double-submit while saving', () => {
      setup({ session: CLIENT });
      pickModel();
      component.line(0).get('reel')?.setValue('3|1.50');
      component.createProforma();
      component.createProforma();
      httpMock.expectOne(`${base}/client/me`).flush(profile);
      httpMock.expectOne(`${base}/invoice`).flush({ id: 1 });
    });

    it('shows the server error in the summary and keeps the quote and the session', () => {
      setup({ session: CLIENT });
      pickModel();
      component.line(0).get('reel')?.setValue('3|1.50');
      component.createProforma();
      httpMock.expectOne(`${base}/client/me`).flush(profile);
      httpMock.expectOne(`${base}/invoice`).flush(
        { non_field_errors: ['No hay precio disponible para la lámina/ancho solicitado'] },
        { status: 400, statusText: 'Bad Request' }
      );
      fixture.detectChanges();

      expect(component.saveError()).toContain('No hay precio disponible');
      expect(text()).toContain('No hay precio disponible');
      expect(component.saving()).toBeFalse();
      expect(component.creating()).toBeFalse();
      expect(router.navigate).not.toHaveBeenCalled();
      expect(component.quote().total).toBe(388);
    });

    it('explains a missing client profile (404 on client/me)', () => {
      setup({ session: CLIENT });
      pickModel();
      component.line(0).get('reel')?.setValue('3|1.50');
      component.createProforma();
      httpMock.expectOne(`${base}/client/me`).flush({ detail: 'x' }, { status: 404, statusText: 'Not Found' });
      expect(component.saveError()).toContain('no tiene un perfil de cliente');
      httpMock.expectNone(`${base}/invoice`);
    });

    it('with an expired token it reopens the access modal without losing the quote and retries the save', async () => {
      setup({ session: CLIENT });
      pickModel();
      quoteTwoItems();
      component.createProforma();
      httpMock.expectOne(`${base}/client/me`).flush(profile);
      acceso.open.and.callFake(() => {
        setSession(CLIENT);
        return Promise.resolve(true);
      });
      // El interceptor cierra la sesion y avisa; el 401 en si no muestra un error.
      httpMock.expectOne(`${base}/invoice`).flush('x', { status: 401, statusText: 'Unauthorized' });
      setSession({} as User);
      auth.notifySessionExpired();
      await fixture.whenStable();

      expect(acceso.open).toHaveBeenCalledWith('login', jasmine.stringContaining('venció'));
      expect(component.saveError()).toBe('');
      expect(component.quote().total).toBe(498);
      httpMock.match(`${base}/client/me`).forEach((r) => r.flush(profile));
      httpMock.expectOne(`${base}/invoice`).flush({ id: 50 });
      expect(router.navigate).toHaveBeenCalledWith(['/mis-proformas'], { state: { savedId: 50 } });
    });

    it('ignores the expired-session event when nothing is being saved', async () => {
      setup({ session: CLIENT });
      auth.notifySessionExpired();
      await fixture.whenStable();
      expect(acceso.open).not.toHaveBeenCalled();
    });
  });

  describe('staff', () => {
    it('keeps the v1 path: opens the internal form with the quote as navigation state', () => {
      setup({ session: STAFF });
      pickModel();
      component.line(0).get('reel')?.setValue('3|1.50');
      expect(text()).toContain('Crear Proforma');

      component.createProforma();

      expect(router.navigate).toHaveBeenCalledWith(['/ordenes/proformas/create'], {
        state: {
          cotizacion: {
            version: 1, sucursal: 1, carModelId: 9,
            lines: [{ carPartId: 5, windowFilm: 3, width: '1.50', length: '1.20', quantity: 2 }],
          },
        },
      });
      httpMock.expectNone(`${base}/invoice`);
      expect(acceso.open).not.toHaveBeenCalled();
    });

    it('hides "Crear Proforma" without the add_proforma_header permission', () => {
      staffCanCreate = false;
      setup({ session: STAFF });
      pickModel();
      expect(text()).not.toContain('Crear Proforma');
      expect(text()).toContain('Consultar por WhatsApp');
    });
  });

  describe('acceso desde la ruta (?acceso=1)', () => {
    it('opens the modal for an anonymous visitor and goes to "Mis proformas" after signing in', async () => {
      setup({ query: { acceso: '1' } });
      expect(acceso.open).toHaveBeenCalledWith('login', jasmine.stringContaining('ver tus proformas'));
      await fixture.whenStable();
      // El espia del modal se cierra sin iniciar sesion: vuelve a la calculadora limpia.
      expect(router.navigate).toHaveBeenCalledWith(['/calculadora'], { replaceUrl: true });
    });
  });
});
