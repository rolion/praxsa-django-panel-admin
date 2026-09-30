import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/service/auth.service';
import { AppInstalador } from '../users.model';
import { InstaladoresListComponent } from './instaladores-list.component';

const sample: AppInstalador[] = [
  { id: 1, name: 'Pedro', address: 'Av. 1', phonenumber: '70012345', sucursal: [1], sucursal_names: ['Central'], is_active: true },
  { id: 2, name: 'Maria', address: 'Av. 2', phonenumber: '70012346', sucursal: [1, 2], sucursal_names: ['Central', 'Norte'], is_active: true },
];

function loginAs(httpMock: HttpTestingController, authService: AuthService, groups: string[]): void {
  authService.login('user', 'pass').subscribe();
  httpMock
    .expectOne(`${environment.apiUrl}/product/api-panel-admin-token-auth/`)
    .flush({ token: 't', user_id: 1, username: 'user', name: 'U', lastname: 'U', is_staff: true, groups });
}

describe('InstaladoresListComponent', () => {
  let component: InstaladoresListComponent;
  let httpMock: HttpTestingController;
  let authService: AuthService;
  const base = `${environment.apiUrl}/product/instaladores`;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [InstaladoresListComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), NgbModal],
    });
    httpMock = TestBed.inject(HttpTestingController);
    authService = TestBed.inject(AuthService);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  function createComponent() {
    const fixture = TestBed.createComponent(InstaladoresListComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    httpMock.expectOne((r) => r.url === base).flush(sample);
    return fixture;
  }

  it('loads instaladores into rows', () => {
    createComponent();

    expect(component.rows).toEqual(sample);
  });

  it('filterDatatable() matches by name', () => {
    createComponent();

    component.filterDatatable({ target: { value: 'mar' } } as unknown as Event);

    expect(component.rows.map((r) => r.id)).toEqual([2]);
  });

  it('shows an error message when the list fails to load', () => {
    const fixture = TestBed.createComponent(InstaladoresListComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    httpMock.expectOne((r) => r.url === base).flush('boom', { status: 500, statusText: 'Server Error' });

    expect(component.errorMessage).toContain('No se pudo cargar');
  });

  it('canManage is false for a non-admin group', () => {
    loginAs(httpMock, authService, ['almacen']);
    createComponent();

    expect(component.canManage).toBe(false);
  });

  it('canManage is true for the admin group', () => {
    loginAs(httpMock, authService, ['admin']);
    createComponent();

    expect(component.canManage).toBe(true);
  });

  it('save() does not call the API when the form is invalid', () => {
    createComponent();
    component.form.patchValue({ name: '', address: '', phonenumber: 'abc', sucursal: [] });

    component.save();

    expect(component.submitted).toBe(true);
    httpMock.expectNone(base);
  });

  it('save() POSTs a new instalador and reloads the list', () => {
    createComponent();
    component.editingId = null;
    component.form.setValue({ name: 'Juan', address: 'Av. 3', phonenumber: '70012347', sucursal: [1, 2] });

    component.save();

    const req = httpMock.expectOne((r) => r.url === base && r.method === 'POST');
    expect(req.request.body).toEqual({ name: 'Juan', address: 'Av. 3', phonenumber: '70012347', sucursal: [1, 2] });
    req.flush({ ...sample[0], id: 3, name: 'Juan' });
    httpMock.expectOne((r) => r.url === base && r.method === 'GET').flush(sample);
  });

  it('save() PATCHes when editing and shows the server error', () => {
    createComponent();
    component.editingId = 2;
    component.form.setValue({ name: 'Maria', address: 'Av. 2', phonenumber: '70012346', sucursal: [1] });

    component.save();

    const req = httpMock.expectOne(`${base}/2/`);
    expect(req.request.method).toBe('PATCH');
    req.flush({ phonenumber: ['Enter a valid value.'] }, { status: 400, statusText: 'Bad Request' });
    expect(component.formError).toBe('Enter a valid value.');
    expect(component.saving).toBe(false);
  });
});
