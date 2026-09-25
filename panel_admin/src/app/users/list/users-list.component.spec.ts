import { TestBed } from '@angular/core/testing';
import { importProvidersFrom } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { FeatherModule } from 'angular-feather';
import { allIcons } from 'angular-feather/icons';
import Swal from 'sweetalert2';
import { environment } from '../../../environments/environment';
import { UsersListComponent } from './users-list.component';
import { AppUser } from '../users.model';

const sampleUsers: AppUser[] = [
  {
    id: 1,
    username: 'ana@test.com',
    email: 'ana@test.com',
    first_name: 'Ana',
    last_name: 'Perez',
    is_active: true,
    is_staff: true,
    phone_number: '70000000',
    groups: [],
    sucursales: [],
  },
];

describe('UsersListComponent', () => {
  let component: UsersListComponent;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [UsersListComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        importProvidersFrom(FeatherModule.pick(allIcons)),
      ],
    });
    const fixture = TestBed.createComponent(UsersListComponent);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('loads users from the API into rows (active only by default)', () => {
    component.ngOnInit();

    const req = httpMock.expectOne(
      (r) => r.url === `${environment.apiUrl}/product/users`
    );
    expect(req.request.params.has('include_inactive')).toBe(false);
    req.flush(sampleUsers);

    expect(component.rows).toEqual(sampleUsers);
    expect(component.loadingIndicator).toBe(false);
  });

  it('requests inactive users too when the toggle is on', () => {
    component.includeInactive = true;
    component.onToggleIncludeInactive();

    const req = httpMock.expectOne(
      (r) => r.url === `${environment.apiUrl}/product/users`
    );
    expect(req.request.params.get('include_inactive')).toBe('true');
    req.flush([]);
  });

  it('deactivate() confirms and calls toggle-active with false', () => {
    spyOn(Swal, 'fire').and.returnValue(Promise.resolve({ isConfirmed: true } as any));
    component.rows = sampleUsers;

    component.deactivate(sampleUsers[0]);

    return Promise.resolve().then(() => {
      const req = httpMock.expectOne(
        `${environment.apiUrl}/product/users/1/toggle-active/`
      );
      expect(req.request.body).toEqual({ is_active: false });
      req.flush({ ...sampleUsers[0], is_active: false });
      httpMock.expectOne(`${environment.apiUrl}/product/users`).flush([]);
    });
  });
});
