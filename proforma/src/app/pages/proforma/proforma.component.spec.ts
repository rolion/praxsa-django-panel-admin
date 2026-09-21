import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { NO_ERRORS_SCHEMA } from '@angular/core';

import { ProformaComponent } from './proforma.component';

describe('ProformaComponent', () => {
  let component: ProformaComponent;
  let fixture: ComponentFixture<ProformaComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ProformaComponent ],
      imports: [HttpClientTestingModule, RouterTestingModule],
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({}) } } }
      ],
      schemas: [NO_ERRORS_SCHEMA]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ProformaComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
