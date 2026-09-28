import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/service/auth.service';
import { AppWindowFilm } from '../almacen.model';
import { LaminasListComponent } from './laminas-list.component';

const sampleLaminas: AppWindowFilm[] = [
  { id: 1, name: 'Carbon 20%', description: 'oscuro', content: null, image: null, is_active: true },
  { id: 2, name: 'Ceramico 30%', description: 'claro', content: null, image: null, is_active: true },
];

function loginAs(httpMock: HttpTestingController, authService: AuthService, groups: string[]): void {
  authService.login('user', 'pass').subscribe();
  httpMock
    .expectOne(`${environment.apiUrl}/product/api-panel-admin-token-auth/`)
    .flush({ token: 't', user_id: 1, username: 'user', name: 'U', lastname: 'U', is_staff: true, groups });
}

describe('LaminasListComponent', () => {
  let component: LaminasListComponent;
  let httpMock: HttpTestingController;
  let authService: AuthService;
  const base = `${environment.apiUrl}/product/almacen/laminas`;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [LaminasListComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    httpMock = TestBed.inject(HttpTestingController);
    authService = TestBed.inject(AuthService);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  function createComponent() {
    const fixture = TestBed.createComponent(LaminasListComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    return fixture;
  }

  it('loads laminas from the API into rows', () => {
    createComponent();
    const req = httpMock.expectOne((r) => r.url === base);
    req.flush(sampleLaminas);

    expect(component.rows).toEqual(sampleLaminas);
  });

  it('filterDatatable() matches by name', () => {
    createComponent();
    httpMock.expectOne((r) => r.url === base).flush(sampleLaminas);

    component.filterDatatable({ target: { value: 'carbon' } } as unknown as Event);

    expect(component.rows.map((r) => r.name)).toEqual(['Carbon 20%']);
  });

  it('canManage is false for a user in the almacen group', () => {
    loginAs(httpMock, authService, ['almacen']);
    createComponent();
    httpMock.expectOne((r) => r.url === base).flush(sampleLaminas);

    expect(component.canManage).toBe(false);
  });

  it('canManage is true for a user in the admin group', () => {
    loginAs(httpMock, authService, ['admin']);
    createComponent();
    httpMock.expectOne((r) => r.url === base).flush(sampleLaminas);

    expect(component.canManage).toBe(true);
  });
});
