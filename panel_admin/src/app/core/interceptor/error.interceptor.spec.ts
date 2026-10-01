import { HttpClient, HTTP_INTERCEPTORS, provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { BehaviorSubject } from 'rxjs';

import { ErrorInterceptor } from './error.interceptor';
import { JwtInterceptor } from './jwt.interceptor';
import { AuthService } from '../service/auth.service';
import { User } from '../models/user';

interface AuthServiceTestAccess {
  currentUserSubject: BehaviorSubject<User>;
}

/** Sesion vencida (401): el staff conserva recarga; el cliente no recarga y se avisa a la
 * pantalla (ADR-pricing-calculator-screen-sesion-cliente-aislamiento, punto 4). */
describe('ErrorInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let auth: AuthService;
  let reloadSpy: jasmine.Spy;
  let expired: number;

  const setSession = (user: User) => (auth as unknown as AuthServiceTestAccess).currentUserSubject.next(user);

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptorsFromDi()),
        provideHttpClientTesting(),
        { provide: HTTP_INTERCEPTORS, useClass: JwtInterceptor, multi: true },
        { provide: HTTP_INTERCEPTORS, useClass: ErrorInterceptor, multi: true },
      ],
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
    auth = TestBed.inject(AuthService);
    // `reload` es un metodo del interceptor para poder espiarlo (location.reload no se puede).
    const interceptor = TestBed.inject(HTTP_INTERCEPTORS).find((i) => i instanceof ErrorInterceptor) as ErrorInterceptor;
    reloadSpy = spyOn(interceptor as unknown as { reload(): void }, 'reload');
    expired = 0;
    auth.sessionExpired$.subscribe(() => expired++);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  const fail401 = () => {
    http.get('/x').subscribe({ error: () => undefined });
    httpMock.expectOne('/x').flush('no', { status: 401, statusText: 'Unauthorized' });
  };

  it('staff: logs out and reloads the page as before', () => {
    setSession({ token: 't', isStaff: true } as User);
    fail401();
    expect(auth.isLoggedIn).toBeFalse();
    expect(reloadSpy).toHaveBeenCalledTimes(1);
    expect(expired).toBe(0);
  });

  it('client: logs out, does NOT reload and notifies the screen', () => {
    setSession({ token: 't', isStaff: false } as User);
    fail401();
    expect(auth.isLoggedIn).toBeFalse();
    expect(reloadSpy).not.toHaveBeenCalled();
    expect(expired).toBe(1);
  });

  it('anonymous call answered with 401 does not reload nor notify', () => {
    setSession({} as User);
    fail401();
    expect(reloadSpy).not.toHaveBeenCalled();
    expect(expired).toBe(0);
  });

  it('other errors are propagated untouched', () => {
    setSession({ token: 't', isStaff: false } as User);
    let status = 0;
    http.get('/x').subscribe({ error: (e) => (status = e.status) });
    httpMock.expectOne('/x').flush('x', { status: 400, statusText: 'Bad Request' });
    expect(status).toBe(400);
    expect(auth.isLoggedIn).toBeTrue();
    expect(reloadSpy).not.toHaveBeenCalled();
  });
});
