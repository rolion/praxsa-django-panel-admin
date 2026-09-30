import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AppGroup, AppSucursal, AppUser } from '../users.model';
import { UserViewComponent } from './user-view.component';

const base = `${environment.apiUrl}/product`;

function makeUser(overrides: Partial<AppUser> = {}): AppUser {
  return {
    id: 7,
    username: 'zulma@test.com',
    email: 'zulma@test.com',
    first_name: 'Zulma',
    last_name: 'Cerezo',
    is_active: true,
    is_staff: true,
    phone_number: '70000000',
    groups: [],
    sucursales: [],
    ...overrides,
  };
}

function makeGroups(n: number): AppGroup[] {
  return Array.from({ length: n }, (_, i) => ({ id: i + 1, name: `Grupo ${i + 1}`, permissions: [] }));
}

function makeSucursales(n: number): AppSucursal[] {
  return Array.from({ length: n }, (_, i) => ({
    id: i + 1,
    name: `Sucursal ${i + 1}`,
    address: '',
    phone_number: null,
    enable_to_install_windows_film: false,
  }));
}

describe('UserViewComponent', () => {
  let httpMock: HttpTestingController;

  function render(user: AppUser, groups: AppGroup[], sucursales: AppSucursal[]) {
    const fixture = TestBed.createComponent(UserViewComponent);
    fixture.detectChanges();
    httpMock.expectOne(`${base}/users/7/`).flush(user);
    httpMock.expectOne(`${base}/groups`).flush(groups);
    httpMock.expectOne(`${base}/sucursales`).flush(sucursales);
    fixture.detectChanges();
    return fixture;
  }

  const q = (fixture: { nativeElement: HTMLElement }, sel: string) =>
    fixture.nativeElement.querySelectorAll<HTMLElement>(sel);

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [UserViewComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => '7' } } } },
      ],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('shows the full name as title and falls back to username when empty', () => {
    const fixture = render(makeUser(), [], []);
    expect(q(fixture, '[data-test="full-name"]')[0].textContent.trim()).toBe('Zulma Cerezo');

    const empty = TestBed.createComponent(UserViewComponent);
    empty.componentInstance.user = makeUser({ first_name: '', last_name: '' });
    expect(empty.componentInstance.fullName).toBe('zulma@test.com');
  });

  it('shows the status badge according to is_active', () => {
    const active = render(makeUser({ is_active: true }), [], []);
    const badge = q(active, '[data-test="status"]')[0];
    expect(badge.textContent.trim()).toBe('Activo');
    expect(badge.classList).toContain('bg-success');
  });

  it('shows Inactivo with the secondary badge when the user is inactive', () => {
    const fixture = render(makeUser({ is_active: false }), [], []);
    const badge = q(fixture, '[data-test="status"]')[0];
    expect(badge.textContent.trim()).toBe('Inactivo');
    expect(badge.classList).toContain('bg-secondary');
  });

  it('shows the phone placeholder when there is no phone number', () => {
    const fixture = render(makeUser({ phone_number: null }), [], []);
    expect(fixture.nativeElement.textContent).toContain('—');
  });

  it('shows neutral empty states without groups or sucursales', () => {
    const fixture = render(makeUser(), makeGroups(2), makeSucursales(2));
    expect(fixture.nativeElement.textContent).toContain('Sin grupos');
    expect(fixture.nativeElement.textContent).toContain('Sin sucursales');
  });

  it('shows all chips and no counter with 2 items', () => {
    const fixture = render(makeUser({ groups: [1, 2], sucursales: [1, 2] }), makeGroups(2), makeSucursales(2));
    expect(q(fixture, '[data-test="group-chip"]').length).toBe(2);
    expect(q(fixture, '[data-test="sucursal-chip"]').length).toBe(2);
    expect(q(fixture, '[data-test="groups-toggle"]').length).toBe(0);
    expect(q(fixture, '[data-test="sucursales-toggle"]').length).toBe(0);
  });

  it('shows 3 chips and no counter with exactly 3 items', () => {
    const fixture = render(makeUser({ groups: [1, 2, 3] }), makeGroups(3), []);
    expect(q(fixture, '[data-test="group-chip"]').length).toBe(3);
    expect(q(fixture, '[data-test="groups-toggle"]').length).toBe(0);
  });

  it('caps at 3 chips with "+N más" and expands / collapses on click', () => {
    const fixture = render(
      makeUser({ groups: [1, 2, 3, 4, 5], sucursales: [1, 2, 3, 4, 5, 6] }),
      makeGroups(5),
      makeSucursales(6)
    );
    expect(q(fixture, '[data-test="group-chip"]').length).toBe(3);
    const toggle = q(fixture, '[data-test="groups-toggle"]')[0];
    expect(toggle.textContent.trim()).toBe('+2 más');
    expect(q(fixture, '[data-test="sucursales-toggle"]')[0].textContent.trim()).toBe('+3 más');

    toggle.click();
    fixture.detectChanges();
    expect(q(fixture, '[data-test="group-chip"]').length).toBe(5);
    expect(q(fixture, '[data-test="groups-toggle"]')[0].textContent.trim()).toBe('Ver menos');
    expect(q(fixture, '[data-test="sucursal-chip"]').length).toBe(3);

    q(fixture, '[data-test="groups-toggle"]')[0].click();
    fixture.detectChanges();
    expect(q(fixture, '[data-test="group-chip"]').length).toBe(3);
  });
});
