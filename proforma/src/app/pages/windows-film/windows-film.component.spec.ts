import { ComponentFixture, TestBed } from '@angular/core/testing';

import { WindowsFilmComponent } from './windows-film.component';

describe('WindowsFilmComponent', () => {
  let component: WindowsFilmComponent;
  let fixture: ComponentFixture<WindowsFilmComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [WindowsFilmComponent]
    });
    fixture = TestBed.createComponent(WindowsFilmComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
