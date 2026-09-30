import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { importProvidersFrom } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { FeatherModule } from 'angular-feather';
import { allIcons } from 'angular-feather/icons';
import { provideTranslateService } from '@ngx-translate/core';
import { DirectionService } from '@core';
import { MinimalLayoutComponent } from './minimal-layout.component';

describe('MinimalLayoutComponent', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [MinimalLayoutComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        provideTranslateService(),
        DirectionService,
        importProvidersFrom(FeatherModule.pick(allIcons)),
      ],
    });
  });

  afterEach(() => localStorage.clear());

  it('renders only the minimal header and the outlet, without sidebars', () => {
    const fixture = TestBed.createComponent(MinimalLayoutComponent);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;

    expect(el.querySelector('.layout-minimal')).not.toBeNull();
    expect(el.querySelector('app-header .header-brand')).not.toBeNull();
    expect(el.querySelector('app-sidebar')).toBeNull();
    expect(el.querySelector('app-right-sidebar')).toBeNull();
    expect(el.querySelector('router-outlet')).not.toBeNull();
  });
});
