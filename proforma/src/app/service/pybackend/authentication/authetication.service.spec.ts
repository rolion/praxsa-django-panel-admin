import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';

import { AutheticationService } from './authetication.service';

describe('AutheticationService', () => {
  let service: AutheticationService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule]
    });
    service = TestBed.inject(AutheticationService);
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('logout() limpia también la clave email de localStorage (paridad con login())', () => {
    localStorage.setItem('token', 'test-token');
    localStorage.setItem('name', 'Nombre');
    localStorage.setItem('lastname', 'Apellido');
    localStorage.setItem('phone_number', '70000000');
    localStorage.setItem('email', 'user@test.com');
    localStorage.setItem('ci_nit', '1234567');

    service.logout();

    expect(localStorage.getItem('email')).toBeNull();
    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('name')).toBeNull();
    expect(localStorage.getItem('lastname')).toBeNull();
    expect(localStorage.getItem('phone_number')).toBeNull();
    expect(localStorage.getItem('ci_nit')).toBeNull();
  });
});
