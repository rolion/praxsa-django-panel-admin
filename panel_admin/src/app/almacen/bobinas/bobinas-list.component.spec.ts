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
import { AppWindowFilmReel } from '../almacen.model';
import { BobinasListComponent } from './bobinas-list.component';

const sampleReels: AppWindowFilmReel[] = [
  { id: 1, window_film: 1, window_film_name: 'Carbon 20%', width: '1.50', length: '30.00', price: '120.00', is_active: true },
  { id: 2, window_film: 2, window_film_name: 'Ceramico 30%', width: '1.80', length: '30.00', price: '150.00', is_active: true },
];

function loginAs(httpMock: HttpTestingController, authService: AuthService, groups: string[]): void {
  authService.login('user', 'pass').subscribe();
  httpMock
    .expectOne(`${environment.apiUrl}/product/api-panel-admin-token-auth/`)
    .flush({ token: 't', user_id: 1, username: 'user', name: 'U', lastname: 'U', is_staff: true, groups });
}

describe('BobinasListComponent', () => {
  let component: BobinasListComponent;
  let httpMock: HttpTestingController;
  let authService: AuthService;
  const base = `${environment.apiUrl}/product/almacen/bobinas`;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [BobinasListComponent],
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
    const fixture = TestBed.createComponent(BobinasListComponent);
    component = fixture.componentInstance;
    component.ngOnInit();
    return fixture;
  }

  it('loads bobinas from the API into rows', () => {
    createComponent();
    httpMock.expectOne((r) => r.url === base).flush(sampleReels);

    expect(component.rows).toEqual(sampleReels);
  });

  it('filterDatatable() matches by lamina name', () => {
    createComponent();
    httpMock.expectOne((r) => r.url === base).flush(sampleReels);

    component.filterDatatable({ target: { value: 'ceramico' } } as unknown as Event);

    expect(component.rows.map((r) => r.id)).toEqual([2]);
  });

  it('canManage is false for the almacen group', () => {
    loginAs(httpMock, authService, ['almacen']);
    createComponent();
    httpMock.expectOne((r) => r.url === base).flush(sampleReels);

    expect(component.canManage).toBe(false);
  });

  it('canManage is true for the admin group', () => {
    loginAs(httpMock, authService, ['admin']);
    createComponent();
    httpMock.expectOne((r) => r.url === base).flush(sampleReels);

    expect(component.canManage).toBe(true);
  });
});
