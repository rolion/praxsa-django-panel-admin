import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { importProvidersFrom } from '@angular/core';
import { FeatherModule } from 'angular-feather';
import { allIcons } from 'angular-feather/icons';
import { SidebarComponent } from './sidebar.component';
describe('SidebarComponent', () => {
  let component: SidebarComponent;
  let fixture: ComponentFixture<SidebarComponent>;
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
    imports: [SidebarComponent],
    providers: [
      provideHttpClient(),
      provideHttpClientTesting(),
      provideRouter([]),
      importProvidersFrom(FeatherModule.pick(allIcons)),
    ],
}).compileComponents();
  }));
  beforeEach(() => {
    fixture = TestBed.createComponent(SidebarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });
  it('should create', () => {
    expect(component).toBeTruthy();
  });
  it('renderiza el logo completo y el simbolo Rx del menu cerrado', () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('img.logo-full')?.getAttribute('src')).toBe('assets/images/praxsa-admin-logo-full.webp');
    expect(el.querySelector('img.logo-mark')?.getAttribute('src')).toBe('assets/images/praxsa-rx-mark.png');
  });
});
