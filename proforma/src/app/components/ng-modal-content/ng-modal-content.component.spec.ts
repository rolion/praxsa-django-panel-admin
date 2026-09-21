import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';

import { NgModalContentComponent } from './ng-modal-content.component';

describe('NgModalContentComponent', () => {
  let component: NgModalContentComponent;
  let fixture: ComponentFixture<NgModalContentComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ NgModalContentComponent ],
      imports: [HttpClientTestingModule, RouterTestingModule],
      providers: [NgbActiveModal],
      schemas: [NO_ERRORS_SCHEMA]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(NgModalContentComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
