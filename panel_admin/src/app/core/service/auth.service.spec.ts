import { TestBed } from '@angular/core/testing';
import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { AuthService } from './auth.service';
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
    req.flush({ token: 'abc123', user_id: 1, username: 'admin', name: 'Ana', lastname: 'Gomez' });
  });

  it('maps the response to a User and persists/emits it on success', () => {
    let emitted: User | undefined;
    service.login('admin', 'secret123').subscribe((user) => (emitted = user));

    httpMock
      .expectOne(loginUrl)
      .flush({ token: 'abc123', user_id: 1, username: 'admin', name: 'Ana', lastname: 'Gomez' });

    expect(emitted).toEqual({
      id: 1,
      username: 'admin',
      firstName: 'Ana',
      lastName: 'Gomez',
      token: 'abc123',
    });
    expect(service.currentUserValue.token).toBe('abc123');
  });

  it('falls back to username as firstName when the backend name is empty', () => {
    let emitted: User | undefined;
    service.login('admin', 'secret123').subscribe((user) => (emitted = user));

    httpMock
      .expectOne(loginUrl)
      .flush({ token: 'abc123', user_id: 1, username: 'admin', name: '', lastname: '' });

    expect(emitted?.firstName).toBe('admin');
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
