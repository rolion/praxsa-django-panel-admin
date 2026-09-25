import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';
import { UserCreateComponent } from './user-create.component';

describe('UserCreateComponent (wizard)', () => {
  let component: UserCreateComponent;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [UserCreateComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    const fixture = TestBed.createComponent(UserCreateComponent);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);

    component.ngOnInit();
    httpMock.expectOne(`${environment.apiUrl}/product/groups`).flush([
      { id: 10, name: 'caja', permissions: [] },
    ]);
    httpMock.expectOne(`${environment.apiUrl}/product/sucursales`).flush([
      { id: 20, name: 'Sucursal Centro', address: '', phone_number: null, enable_to_install_windows_film: true },
    ]);
  });

  afterEach(() => httpMock.verify());

  it('starts on step 1', () => {
    expect(component.step).toBe(1);
  });

  it('does not advance past step 1 with invalid credentials', () => {
    component.goToStep(2);
    expect(component.step).toBe(1);
  });

  it('does not advance past step 1 when passwords do not match', () => {
    component.credentialsForm.setValue({
      username: 'nuevo@test.com',
      password: 'abc123XYZ',
      password_confirm: 'distinta',
      is_active: true,
    });
    component.goToStep(2);
    expect(component.step).toBe(1);
  });

  it('advances through all 4 steps with valid data', () => {
    component.credentialsForm.setValue({
      username: 'nuevo@test.com',
      password: 'abc123XYZ',
      password_confirm: 'abc123XYZ',
      is_active: true,
    });
    component.goToStep(2);
    expect(component.step).toBe(2);

    component.goToStep(3);
    expect(component.step).toBe(3);

    component.goToStep(4);
    expect(component.step).toBe(4);
  });

  it('confirm() sends a single POST with the full combined payload', () => {
    component.credentialsForm.setValue({
      username: 'nuevo@test.com',
      password: 'abc123XYZ',
      password_confirm: 'abc123XYZ',
      is_active: true,
    });
    component.profileForm.patchValue({
      first_name: 'Nuevo',
      last_name: 'Usuario',
      email: 'nuevo@test.com',
      phone_number: '70000001',
      sucursales: [20],
    });
    component.groupsForm.patchValue({ groups: [10] });
    component.step = 4;

    component.confirm();

    const req = httpMock.expectOne(`${environment.apiUrl}/product/users`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      username: 'nuevo@test.com',
      password: 'abc123XYZ',
      password_confirm: 'abc123XYZ',
      is_active: true,
      first_name: 'Nuevo',
      last_name: 'Usuario',
      email: 'nuevo@test.com',
      phone_number: '70000001',
      sucursales: [20],
      groups: [10],
    });
    req.flush({ id: 99 });
  });
});
