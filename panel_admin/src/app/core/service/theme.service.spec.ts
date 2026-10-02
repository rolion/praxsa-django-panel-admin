import { TestBed } from '@angular/core/testing';
import { ThemeService } from './theme.service';

describe('ThemeService', () => {
  let service: ThemeService;
  const body = document.body;
  const reset = () => {
    localStorage.clear();
    body.className = '';
  };

  beforeEach(() => {
    reset();
    TestBed.configureTestingModule({});
    service = TestBed.inject(ThemeService);
  });

  afterEach(reset);

  it('dark: sets the body classes and persists the raw keys', () => {
    service.applyMode('dark', true);

    expect(body.classList.contains('dark')).toBeTrue();
    expect(body.classList.contains('dark-sidebar')).toBeTrue();
    expect(body.classList.contains('theme-black')).toBeTrue();
    expect(body.classList.contains('light')).toBeFalse();
    expect(body.classList.contains('light-sidebar')).toBeFalse();
    expect(body.classList.contains('theme-white')).toBeFalse();
    expect(service.isDark()).toBeTrue();
    expect(localStorage.getItem('theme')).toBe('dark');
    expect(localStorage.getItem('menuOption')).toBe('dark-sidebar');
    expect(localStorage.getItem('choose_skin')).toBe('theme-black');
  });

  it('light: is symmetric to dark', () => {
    service.applyMode('dark', true);
    service.applyMode('light', true);

    expect(body.classList.contains('light')).toBeTrue();
    expect(body.classList.contains('light-sidebar')).toBeTrue();
    expect(body.classList.contains('theme-white')).toBeTrue();
    expect(body.classList.contains('dark')).toBeFalse();
    expect(body.classList.contains('dark-sidebar')).toBeFalse();
    expect(body.classList.contains('theme-black')).toBeFalse();
    expect(service.isDark()).toBeFalse();
    expect(localStorage.getItem('theme')).toBe('light');
  });

  it('toggle alternates the mode', () => {
    service.applyMode('light', false);
    service.toggle();
    expect(service.isDark()).toBeTrue();
    service.toggle();
    expect(service.isDark()).toBeFalse();
  });

  it('applyMode without persist does not write to localStorage', () => {
    service.applyMode('dark', false);

    expect(body.classList.contains('dark')).toBeTrue();
    expect(localStorage.getItem('theme')).toBeNull();
    expect(localStorage.getItem('menuOption')).toBeNull();
    expect(localStorage.getItem('choose_skin')).toBeNull();
  });

  it('applySaved restores the stored dark mode', () => {
    localStorage.setItem('theme', 'dark');
    service.applySaved();

    expect(service.isDark()).toBeTrue();
    expect(body.classList.contains('dark')).toBeTrue();
  });

  it('applySaved falls back to the configured variant (light) when nothing is stored', () => {
    service.applySaved();

    expect(service.isDark()).toBeFalse();
    expect(body.classList.contains('light')).toBeTrue();
    expect(body.classList.contains('theme-white')).toBeTrue();
  });

  it('removes leftover legacy skin classes', () => {
    body.classList.add('theme-purple', 'light');
    service.applyMode('dark', false);

    expect(body.classList.contains('theme-purple')).toBeFalse();
    expect(body.classList.contains('theme-black')).toBeTrue();
  });
});
