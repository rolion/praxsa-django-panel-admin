import { TestBed } from '@angular/core/testing';
import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { AuthService } from './auth.service';
import { LocalStorageService } from './storage.service';
import { User } from '../models/user';
import { environment } from '../../../environments/environment';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;

  const loginUrl = `${environment.apiUrl}/product/api-panel-admin-token-auth/`;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('posts credentials to the panel_admin auth endpoint', () => {
    service.login('admin', 'secret123').subscribe();

    const req = httpMock.expectOne(loginUrl);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ username: 'admin', password: 'secret123' });
    req.flush({
      token: 'abc123', user_id: 1, username: 'admin', name: 'Ana', lastname: 'Gomez',
      is_staff: true, groups: ['admin'],
    });
  });

  it('maps the response to a User and persists/emits it on success', () => {
    let emitted: User | undefined;
    service.login('admin', 'secret123').subscribe((user) => (emitted = user));

    httpMock
      .expectOne(loginUrl)
      .flush({
        token: 'abc123', user_id: 1, username: 'admin', name: 'Ana', lastname: 'Gomez',
        is_staff: true, groups: ['admin'],
      });

    expect(emitted).toEqual({
      id: 1,
      username: 'admin',
      firstName: 'Ana',
      lastName: 'Gomez',
      token: 'abc123',
      isStaff: true,
      groups: ['admin'],
      permissions: [],
    });
    expect(service.currentUserValue.token).toBe('abc123');
  });

  it('stores the effective permissions returned by the login and hasPermission matches them', () => {
    service.login('admin', 'secret123').subscribe();
    httpMock
      .expectOne(loginUrl)
      .flush({
        token: 'abc123', user_id: 1, username: 'admin', name: 'Ana', lastname: 'Gomez',
        is_staff: true, groups: ['admin'],
        permissions: ['product.add_proforma_header', 'product.change_nota_trabajo'],
      });

    expect(service.currentUserValue.permissions).toEqual([
      'product.add_proforma_header', 'product.change_nota_trabajo',
    ]);
    expect(service.hasPermission('add_proforma_header')).toBe(true);
    expect(service.hasPermission('product.change_nota_trabajo')).toBe(true);
    expect(service.hasPermission('change_proforma_header')).toBe(false);
  });

  it('hasPermission is false without a logged-in user or for a session saved without permissions', () => {
    expect(service.hasPermission('add_proforma_header')).toBe(false);
    TestBed.inject(LocalStorageService).set('currentUser', { id: 1, token: 't', groups: ['admin'] });
    const restored = TestBed.runInInjectionContext(() => new AuthService());
    expect(restored.currentUserValue.token).toBe('t');
    expect(restored.hasPermission('add_proforma_header')).toBe(false);
  });

  it('falls back to username as firstName when the backend name is empty', () => {
    let emitted: User | undefined;
    service.login('admin', 'secret123').subscribe((user) => (emitted = user));

    httpMock
      .expectOne(loginUrl)
      .flush({
        token: 'abc123', user_id: 1, username: 'admin', name: '', lastname: '',
        is_staff: true, groups: [],
      });

    expect(emitted?.firstName).toBe('admin');
  });

  it('hasGroup matches case-insensitively against the logged-in user groups', () => {
    service.login('almacen', 'secret123').subscribe();
    httpMock
      .expectOne(loginUrl)
      .flush({
        token: 'abc123', user_id: 2, username: 'almacen', name: 'Al', lastname: 'Macen',
        is_staff: true, groups: ['Almacen'],
      });

    expect(service.hasGroup('almacen')).toBe(true);
    expect(service.hasGroup('admin')).toBe(false);
  });

  it('hasGroup is false when there is no logged-in user', () => {
    expect(service.hasGroup('admin')).toBe(false);
  });

  it('propagates the error without persisting a user on invalid credentials', () => {
    let error: HttpErrorResponse | undefined;
    service.login('admin', 'wrong').subscribe({ error: (err) => (error = err) });

    httpMock
      .expectOne(loginUrl)
      .flush({ non_field_errors: ['Unable to log in with provided credentials.'] }, { status: 400, statusText: 'Bad Request' });

    expect(error?.status).toBe(400);
    expect(service.currentUserValue.token).toBeUndefined();
  });
});
