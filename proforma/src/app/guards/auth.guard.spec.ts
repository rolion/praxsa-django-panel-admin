import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';

import { AuthGuard } from './auth.guard';
import { AutheticationService } from '../service/pybackend/authentication/authetication.service';
import { User } from '../model/user';

describe('AuthGuard', () => {
  let guard: AuthGuard;
  let auth: AutheticationService;
  let router: Router;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [RouterTestingModule, HttpClientTestingModule],
    });

    guard = TestBed.inject(AuthGuard);
    auth = TestBed.inject(AutheticationService);
    router = TestBed.inject(Router);
  });

  it('usuario autenticado: canActivate devuelve true y no navega', () => {
    spyOn(auth, 'getUser').and.returnValue(new User('user@test.com', '', 'Name', 'Lastname', '123', '456'));
    const navigateSpy = spyOn(router, 'navigate');

    const result = guard.canActivate();

    expect(result).toBeTrue();
    expect(navigateSpy).not.toHaveBeenCalled();
  });

  it('usuario no autenticado: canActivate devuelve false y redirige a /login', () => {
    spyOn(auth, 'getUser').and.returnValue(null);
    const navigateSpy = spyOn(router, 'navigate');

    const result = guard.canActivate();

    expect(result).toBeFalse();
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);
  });
});
