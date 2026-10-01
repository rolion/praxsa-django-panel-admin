import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { environment } from '../../environments/environment';
import { AccesoModalComponent, passwordsMatch } from './acceso-modal.component';

const loginUrl = `${environment.apiUrl}/product/api-panel-admin-token-auth/`;
const registerUrl = `${environment.apiUrl}/product/client/register`;
const loginResponse = { token: 'tok', user_id: 7, username: 'ana', name: 'Ana', lastname: 'Gomez', is_staff: false, groups: [], permissions: [] };

describe('AccesoModalComponent', () => {
  let fixture: ComponentFixture<AccesoModalComponent>;
  let component: AccesoModalComponent;
  let httpMock: HttpTestingController;
  let activeModal: { close: jasmine.Spy; dismiss: jasmine.Spy };

  beforeEach(() => {
    localStorage.clear();
    activeModal = { close: jasmine.createSpy('close'), dismiss: jasmine.createSpy('dismiss') };
    TestBed.configureTestingModule({
      imports: [AccesoModalComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), { provide: NgbActiveModal, useValue: activeModal }],
    });
    httpMock = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(AccesoModalComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  const text = () => (fixture.nativeElement as HTMLElement).textContent ?? '';

  const fillStep1 = (overrides: Record<string, string> = {}) =>
    component.step1.patchValue({
      name: 'Ana', lastname: 'Gomez', email: 'ana@test.com', phone_number: '70000001', car_plate: 'ABC123', ...overrides,
    });

  const fillStep2 = (overrides: Record<string, string> = {}) =>
    component.step2.patchValue({ username: 'ana@test.com', password: 'Sup3r-segura', confirm: 'Sup3r-segura', ...overrides });

  describe('iniciar sesion', () => {
    it('starts in login mode', () => {
      expect(component.mode()).toBe('login');
      expect(text()).toContain('Iniciar sesión');
    });

    it('does not send the request with an empty form', () => {
      component.login();
      expect(component.loginForm.invalid).toBeTrue();
      httpMock.expectNone(loginUrl);
    });

    it('logs in with the panel endpoint and closes the modal with true', () => {
      component.loginForm.setValue({ username: 'ana', password: 'secret123' });
      component.login();
      const req = httpMock.expectOne(loginUrl);
      expect(req.request.body).toEqual({ username: 'ana', password: 'secret123' });
      req.flush(loginResponse);
      expect(activeModal.close).toHaveBeenCalledWith(true);
    });

    it('shows "Credenciales inválidas" on a rejected login and re-enables the button', () => {
      component.loginForm.setValue({ username: 'ana', password: 'mala' });
      component.login();
      httpMock.expectOne(loginUrl).flush({ non_field_errors: ['x'] }, { status: 400, statusText: 'Bad Request' });
      expect(component.errorMessage()).toBe('Credenciales inválidas');
      expect(component.busy()).toBeFalse();
      expect(activeModal.close).not.toHaveBeenCalled();
    });

    it('shows a connection message when the server is unreachable', () => {
      component.loginForm.setValue({ username: 'ana', password: 'x' });
      component.login();
      httpMock.expectOne(loginUrl).error(new ProgressEvent('error'), { status: 0 });
      expect(component.errorMessage()).toContain('No se pudo conectar');
    });

    it('does not dismiss while a request is in flight', () => {
      component.busy.set(true);
      component.close();
      expect(activeModal.dismiss).not.toHaveBeenCalled();
      component.busy.set(false);
      component.close();
      expect(activeModal.dismiss).toHaveBeenCalled();
    });
  });

  describe('crear cuenta en 2 etapas', () => {
    beforeEach(() => component.setMode('register'));

    it('shows the 2-step indicator and starts in step 1', () => {
      fixture.detectChanges();
      expect(component.step()).toBe(1);
      expect(text()).toContain('Tus datos');
      expect(text()).toContain('Tu acceso');
    });

    it('blocks "Siguiente" when step 1 is invalid and explains why', () => {
      fillStep1({ email: 'no-es-correo', phone_number: '123' });
      component.nextStep();
      fixture.detectChanges();
      expect(component.step()).toBe(1);
      expect(text()).toContain('Ingresa un correo válido');
      expect(text()).toContain('entre 7 y 11 dígitos');
    });

    it('requires the plate (max 10 characters)', () => {
      fillStep1({ car_plate: '' });
      component.nextStep();
      expect(component.step()).toBe(1);
      fillStep1({ car_plate: 'ABCDEFGHIJK' });
      expect(component.step1.get('car_plate')?.invalid).toBeTrue();
    });

    it('moves to step 2 suggesting the email as the username', () => {
      fillStep1();
      component.nextStep();
      expect(component.step()).toBe(2);
      expect(component.step2.get('username')?.value).toBe('ana@test.com');
    });

    it('keeps a username the person already edited when going forward again', () => {
      fillStep1();
      component.nextStep();
      component.step2.get('username')?.setValue('ana.g');
      component.step2.get('username')?.markAsDirty();
      component.previousStep();
      component.step1.patchValue({ email: 'otro@test.com' });
      component.nextStep();
      expect(component.step2.get('username')?.value).toBe('ana.g');
    });

    it('"Atrás" keeps what was typed', () => {
      fillStep1();
      component.nextStep();
      component.previousStep();
      expect(component.step()).toBe(1);
      expect(component.step1.get('name')?.value).toBe('Ana');
    });

    it('requires matching passwords and does not send the request otherwise', () => {
      fillStep1();
      component.nextStep();
      fillStep2({ confirm: 'otra-clave' });
      component.register();
      fixture.detectChanges();
      expect(component.step2.hasError('mismatch')).toBeTrue();
      expect(text()).toContain('Las contraseñas no coinciden');
      httpMock.expectNone(registerUrl);
    });

    it('requires at least 8 characters', () => {
      fillStep1();
      component.nextStep();
      fillStep2({ password: 'corta', confirm: 'corta' });
      component.register();
      httpMock.expectNone(registerUrl);
    });

    it('rejects a username with spaces', () => {
      fillStep1();
      component.nextStep();
      fillStep2({ username: 'ana g' });
      expect(component.step2.get('username')?.invalid).toBeTrue();
    });

    it('registers, then logs in automatically and closes with true', () => {
      fillStep1();
      component.nextStep();
      fillStep2({ username: 'ana.g' });
      component.register();

      const registerReq = httpMock.expectOne(registerUrl);
      expect(registerReq.request.body).toEqual({
        name: 'Ana', lastname: 'Gomez', email: 'ana@test.com', phone_number: '70000001', car_plate: 'ABC123',
        username: 'ana.g', password: 'Sup3r-segura',
      });
      expect(registerReq.request.body.confirm).toBeUndefined();
      registerReq.flush({ username: 'ana.g' }, { status: 201, statusText: 'Created' });

      const loginReq = httpMock.expectOne(loginUrl);
      expect(loginReq.request.body).toEqual({ username: 'ana.g', password: 'Sup3r-segura' });
      loginReq.flush(loginResponse);
      expect(activeModal.close).toHaveBeenCalledWith(true);
    });

    it('goes back to step 1 when the server rejects a step-1 field (duplicate email)', () => {
      fillStep1();
      component.nextStep();
      fillStep2();
      component.register();
      httpMock.expectOne(registerUrl).flush({ email: ['email ya existe'] }, { status: 400, statusText: 'Bad Request' });
      fixture.detectChanges();
      expect(component.step()).toBe(1);
      expect(text()).toContain('email ya existe');
      expect(component.busy()).toBeFalse();
    });

    it('stays in step 2 and shows the message for username/password errors', () => {
      fillStep1();
      component.nextStep();
      fillStep2();
      component.register();
      httpMock.expectOne(registerUrl).flush(
        { username: ['usuario ya existe'], password: ['Esta contraseña es demasiado común.'] },
        { status: 400, statusText: 'Bad Request' }
      );
      fixture.detectChanges();
      expect(component.step()).toBe(2);
      expect(text()).toContain('usuario ya existe');
      expect(text()).toContain('demasiado común');
    });

    it('clears a server error when the field is edited', () => {
      component.serverErrors.set({ email: 'email ya existe' });
      component.clearServerError('email');
      expect(component.serverErrors()['email']).toBeUndefined();
    });

    it('explains a throttled registration (429)', () => {
      fillStep1();
      component.nextStep();
      fillStep2();
      component.register();
      httpMock.expectOne(registerUrl).flush('x', { status: 429, statusText: 'Too Many Requests' });
      expect(component.errorMessage()).toContain('Demasiados intentos');
    });

    it('if the account was created but the automatic login fails, switches to login with a hint', () => {
      fillStep1();
      component.nextStep();
      fillStep2({ username: 'ana.g' });
      component.register();
      httpMock.expectOne(registerUrl).flush({ username: 'ana.g' }, { status: 201, statusText: 'Created' });
      httpMock.expectOne(loginUrl).flush('x', { status: 500, statusText: 'err' });
      expect(component.mode()).toBe('login');
      expect(component.errorMessage()).toContain('Tu cuenta fue creada');
      expect(component.loginForm.get('username')?.value).toBe('ana.g');
    });

    it('"¿Ya tienes cuenta?" goes back to login', () => {
      component.setMode('login');
      expect(component.mode()).toBe('login');
    });
  });

  describe('passwordsMatch', () => {
    it('is valid when empty or equal and invalid when different', () => {
      const group = (password: string, confirm: string) => ({ get: (n: string) => ({ value: n === 'password' ? password : confirm }) }) as never;
      expect(passwordsMatch(group('', ''))).toBeNull();
      expect(passwordsMatch(group('abc12345', 'abc12345'))).toBeNull();
      expect(passwordsMatch(group('abc12345', 'xyz'))).toEqual({ mismatch: true });
    });
  });
});
