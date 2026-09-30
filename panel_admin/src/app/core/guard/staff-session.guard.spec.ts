import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { StaffGuard } from './staff.guard';
import { SessionGuard } from './session.guard';
import { AuthService } from '../service/auth.service';
import { User } from '../models/user';

// Acceso de solo-test al BehaviorSubject privado de AuthService, para simular sesiones.
interface AuthServiceTestAccess {
  currentUserSubject: BehaviorSubject<User>;
}

const STAFF = { token: 't', isStaff: true } as User;
const CLIENT = { token: 't', isStaff: false } as User;
const ANONYMOUS = {} as User;

describe('StaffGuard / SessionGuard (aislamiento cliente-staff)', () => {
  let auth: AuthService;
  let router: Router;
  let navigateSpy: jasmine.Spy;

  const setSession = (user: User) => (auth as unknown as AuthServiceTestAccess).currentUserSubject.next(user);

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    auth = TestBed.inject(AuthService);
    router = TestBed.inject(Router);
    navigateSpy = spyOn(router, 'navigate');
  });

  afterEach(() => localStorage.clear());

  describe('AuthService session getters', () => {
    it('distinguishes anonymous, client and staff', () => {
      setSession(ANONYMOUS);
      expect([auth.isLoggedIn, auth.isStaff, auth.isClient]).toEqual([false, false, false]);
      setSession(CLIENT);
      expect([auth.isLoggedIn, auth.isStaff, auth.isClient]).toEqual([true, false, true]);
      setSession(STAFF);
      expect([auth.isLoggedIn, auth.isStaff, auth.isClient]).toEqual([true, true, false]);
    });

    it('treats a saved session without isStaff as non-staff', () => {
      setSession({ token: 't' } as User);
      expect(auth.isStaff).toBeFalse();
      expect(auth.isClient).toBeTrue();
    });

    it('emits sessionExpired$ when notified', () => {
      let emitted = 0;
      auth.sessionExpired$.subscribe(() => emitted++);
      auth.notifySessionExpired();
      expect(emitted).toBe(1);
    });
  });

  describe('StaffGuard', () => {
    it('lets staff through', () => {
      setSession(STAFF);
      expect(TestBed.inject(StaffGuard).canActivate()).toBeTrue();
      expect(navigateSpy).not.toHaveBeenCalled();
    });

    it('sends an anonymous visitor to the panel login', () => {
      setSession(ANONYMOUS);
      expect(TestBed.inject(StaffGuard).canActivate()).toBeFalse();
      expect(navigateSpy).toHaveBeenCalledWith(['/authentication/signin']);
    });

    it('sends a client back to the calculator, never to administration', () => {
      setSession(CLIENT);
      expect(TestBed.inject(StaffGuard).canActivate()).toBeFalse();
      expect(navigateSpy).toHaveBeenCalledWith(['/calculadora']);
    });
  });

  describe('SessionGuard', () => {
    it('lets a client through', () => {
      setSession(CLIENT);
      expect(TestBed.inject(SessionGuard).canActivate()).toBeTrue();
    });

    it('sends an anonymous visitor to the calculator with the access modal flag', () => {
      setSession(ANONYMOUS);
      expect(TestBed.inject(SessionGuard).canActivate()).toBeFalse();
      expect(navigateSpy).toHaveBeenCalledWith(['/calculadora'], { queryParams: { acceso: 1 } });
    });

    it('sends staff to the panel (they have no client list)', () => {
      setSession(STAFF);
      expect(TestBed.inject(SessionGuard).canActivate()).toBeFalse();
      expect(navigateSpy).toHaveBeenCalledWith(['/dashboard/main']);
    });
  });
});
