import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { HttpClient, HTTP_INTERCEPTORS, HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';

import { AuthInterceptor } from './app-http-interceptor';
import { LocalStorageService } from './service/local-storage/local-storage.service';
import { AutheticationService } from './service/pybackend/authentication/authetication.service';

describe('AuthInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let localStorageService: LocalStorageService;
  let router: Router;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule, RouterTestingModule],
      providers: [
        { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true },
      ]
    });

    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
    localStorageService = TestBed.inject(LocalStorageService);
    router = TestBed.inject(Router);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('adjunta el header Authorization cuando hay un token guardado (sesion iniciada via AutheticationService)', () => {
    spyOn(localStorageService, 'getData').and.returnValue('fake-token-123');

    http.get('/api/test').subscribe();

    const req = httpMock.expectOne('/api/test');
    expect(req.request.headers.get('Authorization')).toBe('Token fake-token-123');
    req.flush({});
  });

  it('no adjunta el header Authorization cuando no hay token', () => {
    spyOn(localStorageService, 'getData').and.returnValue(null);

    http.get('/api/test').subscribe();

    const req = httpMock.expectOne('/api/test');
    expect(req.request.headers.has('Authorization')).toBeFalse();
    req.flush({});
  });

  it('ante un 401 limpia la sesion (AutheticationService.logout) y redirige a /login, sin tragarse el error', () => {
    spyOn(localStorageService, 'getData').and.returnValue('fake-token-123');
    const auth = TestBed.inject(AutheticationService);
    const logoutSpy = spyOn(auth, 'logout');
    const navigateSpy = spyOn(router, 'navigateByUrl');
    let capturedError: HttpErrorResponse | undefined;

    http.get('/api/test').subscribe({
      next: () => fail('se esperaba que la peticion fallara con 401'),
      error: (err) => (capturedError = err),
    });

    const req = httpMock.expectOne('/api/test');
    req.flush('Unauthorized', { status: 401, statusText: 'Unauthorized' });

    expect(logoutSpy).toHaveBeenCalled();
    expect(navigateSpy).toHaveBeenCalledWith('/login');
    expect(capturedError?.status).toBe(401);
  });

  it('ante un 403 no limpia la sesion ni redirige (puede ser permiso insuficiente con sesion valida), pero propaga el error', () => {
    spyOn(localStorageService, 'getData').and.returnValue('fake-token-123');
    const auth = TestBed.inject(AutheticationService);
    const logoutSpy = spyOn(auth, 'logout');
    const navigateSpy = spyOn(router, 'navigateByUrl');
    let capturedError: HttpErrorResponse | undefined;

    http.get('/api/test').subscribe({
      next: () => fail('se esperaba que la peticion fallara con 403'),
      error: (err) => (capturedError = err),
    });

    const req = httpMock.expectOne('/api/test');
    req.flush('Forbidden', { status: 403, statusText: 'Forbidden' });

    expect(logoutSpy).not.toHaveBeenCalled();
    expect(navigateSpy).not.toHaveBeenCalled();
    expect(capturedError?.status).toBe(403);
  });
});
