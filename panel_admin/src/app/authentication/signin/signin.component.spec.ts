import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter, Router } from '@angular/router';
import { importProvidersFrom } from '@angular/core';
import { FeatherModule } from 'angular-feather';
import { allIcons } from 'angular-feather/icons';
import { SigninComponent } from './signin.component';
import { environment } from '../../../environments/environment';

describe('SigninComponent', () => {
  let component: SigninComponent;
  let fixture: ComponentFixture<SigninComponent>;
  let httpMock: HttpTestingController;
  let router: Router;

  const loginUrl = `${environment.apiUrl}/product/api-panel-admin-token-auth/`;

  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [SigninComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        importProvidersFrom(FeatherModule.pick(allIcons)),
      ],
    }).compileComponents();
  }));
  beforeEach(() => {
    localStorage.clear();
    fixture = TestBed.createComponent(SigninComponent);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    spyOn(router, 'navigate');
    fixture.detectChanges();
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('navigates to /dashboard/main on successful login', () => {
    component.loginForm.setValue({ username: 'admin', password: 'secret123' });
    component.onSubmit();

    const req = httpMock.expectOne(loginUrl);
    req.flush({ token: 'abc123', user_id: 1, username: 'admin', name: 'Ana', lastname: 'Gomez' });

    expect(router.navigate).toHaveBeenCalledWith(['/dashboard/main']);
    expect(component.error).toBe('');
  });

  it('shows "Credenciales inválidas" on a 400 from the backend', () => {
    component.loginForm.setValue({ username: 'admin', password: 'wrong' });
    component.onSubmit();

    const req = httpMock.expectOne(loginUrl);
    req.flush({ non_field_errors: ['Unable to log in with provided credentials.'] }, { status: 400, statusText: 'Bad Request' });

    expect(component.error).toBe('Credenciales inválidas');
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('shows a network error message when the request fails with status 0', () => {
    component.loginForm.setValue({ username: 'admin', password: 'secret123' });
    component.onSubmit();

    const req = httpMock.expectOne(loginUrl);
    req.error(new ProgressEvent('error'), { status: 0, statusText: 'Unknown Error' });

    expect(component.error).toBe('Algo salió mal, inténtalo de nuevo más tarde');
  });

  it('does not call the backend when the form is invalid', () => {
    component.loginForm.setValue({ username: '', password: '' });
    component.onSubmit();

    httpMock.expectNone(loginUrl);
    expect(component.error).toBe('Usuario y contraseña son obligatorios');
  });
});
