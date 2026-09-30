import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { importProvidersFrom } from '@angular/core';
import { FeatherModule } from 'angular-feather';
import { allIcons } from 'angular-feather/icons';
import { provideTranslateService } from '@ngx-translate/core';
import { HeaderComponent } from './header.component';
import { AuthService } from '@core';
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

  it('minimal variant shows the logo, hides the sidebar toggle and keeps fullscreen and the user menu', () => {
    fixture.componentRef.setInput('minimal', true);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.header-brand img')?.getAttribute('src')).toContain('praxsa-admin-logo.png');
    expect(el.querySelector('.navbar-minimal')).not.toBeNull();
    expect(el.querySelector('i-feather[name="menu"]')).toBeNull();
    expect(el.querySelector('i-feather[name="maximize"]')).not.toBeNull();
    expect(el.querySelector('i-feather[name="user"]')).not.toBeNull();
    expect(el.textContent).toContain('Logout');
  });
});
