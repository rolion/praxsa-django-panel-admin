import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { NO_ERRORS_SCHEMA } from '@angular/core';

import { WindowsFilmComponent } from './windows-film.component';

describe('WindowsFilmComponent', () => {
  let component: WindowsFilmComponent;
  let fixture: ComponentFixture<WindowsFilmComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [WindowsFilmComponent],
      imports: [HttpClientTestingModule],
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({}) } } }
      ],
      schemas: [NO_ERRORS_SCHEMA]
    });
    fixture = TestBed.createComponent(WindowsFilmComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
