import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { AuthGuard } from './auth.guard';
import { AuthService } from '../service/auth.service';
import { User } from '../models/user';

// Acceso de solo-test al BehaviorSubject privado de AuthService, para
// simular una sesion sin pasar por un login HTTP real.
interface AuthServiceTestAccess {
  currentUserSubject: BehaviorSubject<User>;
}

describe('AuthGuard', () => {
  let guard: AuthGuard;
  let authService: AuthService;
  let router: Router;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    guard = TestBed.inject(AuthGuard);
    authService = TestBed.inject(AuthService);
    router = TestBed.inject(Router);
  });

  it('redirects to signin when there is no session', () => {
    const navigateSpy = spyOn(router, 'navigate');

    expect(guard.canActivate()).toBe(false);
    expect(navigateSpy).toHaveBeenCalledWith(['/authentication/signin']);
  });

  it('allows navigation once a session with a token exists', () => {
    (authService as unknown as AuthServiceTestAccess).currentUserSubject.next({
      token: 'abc123',
    } as User);

    expect(guard.canActivate()).toBe(true);
  });
});
