import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EliminacionDatosComponent } from './eliminacion-datos.component';

describe('EliminacionDatosComponent', () => {
  let component: EliminacionDatosComponent;
  let fixture: ComponentFixture<EliminacionDatosComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ EliminacionDatosComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(EliminacionDatosComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
