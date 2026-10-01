import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router, provideRouter } from '@angular/router';
import { importProvidersFrom } from '@angular/core';
import { FeatherModule } from 'angular-feather';
import { allIcons } from 'angular-feather/icons';
import { provideTranslateService } from '@ngx-translate/core';
import { HeaderComponent } from './header.component';
import { AuthService } from '@core';
import { AccesoModalService } from '../../cliente/acceso-modal.service';
import { environment } from '../../../environments/environment';

describe('HeaderComponent', () => {
  let component: HeaderComponent;
  let fixture: ComponentFixture<HeaderComponent>;
  let authService: AuthService;
  let httpMock: HttpTestingController;

  const loginUrl = `${environment.apiUrl}/product/api-panel-admin-token-auth/`;

  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [HeaderComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        provideTranslateService(),
        importProvidersFrom(FeatherModule.pick(allIcons)),
      ],
    }).compileComponents();
  }));
  beforeEach(() => {
    localStorage.clear();
    fixture = TestBed.createComponent(HeaderComponent);
    component = fixture.componentInstance;
    authService = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('shows the logged-in user firstName as the display name', () => {
    authService.login('admin', 'secret123').subscribe();
    httpMock
      .expectOne(loginUrl)
      .flush({ token: 'abc123', user_id: 1, username: 'admin', name: 'Ana', lastname: 'Gomez' });

    expect(component.currentUserName).toBe('Ana');
  });

  it('falls back to username when firstName is empty', () => {
    authService.login('admin', 'secret123').subscribe();
    httpMock
      .expectOne(loginUrl)
      .flush({ token: 'abc123', user_id: 1, username: 'admin', name: '', lastname: '' });

    expect(component.currentUserName).toBe('admin');
  });

  it('no longer shows the Profile/Email/Settings links', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const text = compiled.textContent ?? '';
    expect(text).not.toContain('Profile');
    expect(text).not.toContain('Settings');
  });

  it('does not render the removed template widgets', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.current-user-name')).toBeNull();
    expect(el.querySelector('input[type="search"]')).toBeNull();
    expect(el.querySelector('.lang-toggle')).toBeNull();
    expect(el.querySelector('i-feather[name="mail"]')).toBeNull();
    expect(el.querySelector('i-feather[name="bell"]')).toBeNull();
  });

  it('keeps the sidebar toggle, fullscreen and user menu', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('i-feather[name="menu"]')).not.toBeNull();
    expect(el.querySelector('i-feather[name="maximize"]')).not.toBeNull();
    expect(el.querySelector('i-feather[name="user"]')).not.toBeNull();
  });

  it('shows the user name only as the user dropdown title, with Logout', () => {
    authService.login('admin', 'secret123').subscribe();
    httpMock
      .expectOne(loginUrl)
      .flush({ token: 'abc123', user_id: 1, username: 'admin', name: 'Ana', lastname: 'Gomez' });
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.dropdown-title')?.textContent?.trim()).toBe('Ana');
    expect(el.textContent).toContain('Logout');
  });
  it('default variant has no logo', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.header-brand')).toBeNull();
    expect(el.querySelector('.navbar-minimal')).toBeNull();
  });

  describe('variante minima (layout de cliente)', () => {
    const session = (user: object) =>
      (authService as unknown as { currentUserSubject: { next(u: object): void } }).currentUserSubject.next(user);
    const el = () => fixture.nativeElement as HTMLElement;

    beforeEach(() => fixture.componentRef.setInput('minimal', true));

    it('shows the logo (linking to the calculator) and never the sidebar toggle', () => {
      fixture.detectChanges();
      expect(el().querySelector('.header-brand img')?.getAttribute('src')).toContain('praxsa-admin-logo.png');
      expect(el().querySelector('.header-brand')?.getAttribute('href')).toContain('calculadora');
      expect(el().querySelector('.navbar-minimal')).not.toBeNull();
      expect(el().querySelector('i-feather[name="menu"]')).toBeNull();
    });

    it('anonymous: shows "Iniciar sesión" and "Crear cuenta" and no navigation links', () => {
      fixture.detectChanges();
      expect(el().textContent).toContain('Iniciar sesión');
      expect(el().textContent).toContain('Crear cuenta');
      expect(el().querySelector('.header-links')).toBeNull();
      expect(el().querySelector('i-feather[name="user"]')).toBeNull();
    });

    it('anonymous: the buttons open the access modal in the right mode', () => {
      const open = spyOn(TestBed.inject(AccesoModalService), 'open').and.resolveTo(false);
      fixture.detectChanges();
      const buttons = el().querySelectorAll('.header-access button');
      (buttons[0] as HTMLButtonElement).click();
      (buttons[1] as HTMLButtonElement).click();
      expect(open.calls.allArgs()).toEqual([['login'], ['register']]);
    });

    it('client: shows Calculadora and Proformas plus the user menu with Logout, no fullscreen', () => {
      session({ token: 't', isStaff: false, firstName: 'Ana', username: 'ana' });
      fixture.detectChanges();
      const links = Array.from(el().querySelectorAll('.header-links a')).map((a) => a.textContent?.trim());
      expect(links).toEqual(['Calculadora', 'Proformas']);
      expect(el().querySelector('.header-access')).toBeNull();
      expect(el().querySelector('i-feather[name="user"]')).not.toBeNull();
      expect(el().querySelector('i-feather[name="maximize"]')).toBeNull();
      expect(el().querySelector('.dropdown-title')?.textContent?.trim()).toBe('Ana');
      expect(el().textContent).toContain('Logout');
    });

    it('staff: shows a link back to the panel instead of Proformas', () => {
      session({ token: 't', isStaff: true, firstName: 'Sol', username: 'sol' });
      fixture.detectChanges();
      const links = Array.from(el().querySelectorAll('.header-links a')).map((a) => a.textContent?.trim());
      expect(links).toEqual(['Calculadora', 'Panel']);
    });

    it('reacts to the session changing (login / logout) without reloading', () => {
      fixture.detectChanges();
      expect(el().querySelector('.header-access')).not.toBeNull();
      session({ token: 't', isStaff: false, firstName: 'Ana' });
      fixture.detectChanges();
      expect(el().querySelector('.header-links')).not.toBeNull();
      session({});
      fixture.detectChanges();
      expect(el().querySelector('.header-access')).not.toBeNull();
    });

    it('client logout goes back to the public calculator', () => {
      session({ token: 't', isStaff: false, firstName: 'Ana' });
      const navigate = spyOn(TestBed.inject(Router), 'navigate');
      component.logout();
      expect(navigate).toHaveBeenCalledWith(['/calculadora']);
    });

    it('staff logout goes to the panel login', () => {
      session({ token: 't', isStaff: true, firstName: 'Sol' });
      const navigate = spyOn(TestBed.inject(Router), 'navigate');
      component.logout();
      expect(navigate).toHaveBeenCalledWith(['/authentication/signin']);
    });
  });
});
