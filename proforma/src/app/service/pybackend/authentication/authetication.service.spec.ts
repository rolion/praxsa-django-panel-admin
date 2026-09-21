import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';

import { AutheticationService } from './authetication.service';
import { Credentials } from 'src/app/model/credentials';

describe('AutheticationService', () => {
  let service: AutheticationService;
  let httpMock: HttpTestingController;

  const loginResponse = {
    token: 'tok-123',
    name: 'Nombre',
    lastname: 'Apellido',
    phone_number: '70000000',
    email: 'user@test.com',
    ci_nit: '1234567',
  };

  function doLogin(): void {
    service.login(new Credentials('user@test.com', 'x')).subscribe();
    const req = httpMock.expectOne(r => r.url.endsWith('/product/api-token-auth/'));
    req.flush(loginResponse);
  }

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule]
    });
    service = TestBed.inject(AutheticationService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    localStorage.clear();
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('login() persiste solo token y name en localStorage (TASK-004: PII reducido)', () => {
    doLogin();

    expect(localStorage.getItem('token')).toBe('tok-123');
    expect(localStorage.getItem('name')).toBe('Nombre');
    expect(localStorage.getItem('lastname')).toBeNull();
    expect(localStorage.getItem('phone_number')).toBeNull();
    expect(localStorage.getItem('email')).toBeNull();
    expect(localStorage.getItem('ci_nit')).toBeNull();
  });

  it('login() nunca persiste ci_nit (confirmado código muerto para autocompletado)', () => {
    doLogin();

    expect(localStorage.getItem('ci_nit')).toBeNull();
  });

  it('sin recargar la página, getUser() devuelve el usuario completo inmediatamente después del login', () => {
    doLogin();

    const user = service.getUser();

    expect(user?.name).toBe('Nombre');
    expect(user?.lastname).toBe('Apellido');
    expect(user?.email).toBe('user@test.com');
    expect(user?.phone_number).toBe('70000000');
  });

  it('tras un refresh simulado, solo sobreviven token+name (el resto queda vacío)', () => {
    doLogin();

    // Simula lo que pasa al recargar la página: se reconstruye el estado
    // mínimo desde localStorage en vez de leer el estado en memoria.
    const reloaded = (service as any).restoreMinimalSession();

    expect(reloaded.name).toBe('Nombre');
    expect(reloaded.lastname).toBe('');
    expect(reloaded.email).toBe('');
    expect(reloaded.phone_number).toBe('');
  });

  it('logout() limpia las 6 claves legacy de localStorage, incluida email', () => {
    doLogin();
    // Simula PII que hubiera quedado persistido de una sesión anterior a este cambio.
    localStorage.setItem('email', 'huerfano@test.com');

    service.logout();

    for (const key of ['token', 'name', 'lastname', 'phone_number', 'email', 'ci_nit']) {
      expect(localStorage.getItem(key)).toBeNull();
    }
    expect(service.getUser()).toBeNull();
  });
});
