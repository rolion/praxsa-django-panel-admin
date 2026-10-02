import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormControl } from '@angular/forms';
import { OrdenSucursal } from '../ordenes/ordenes.model';
import { SucursalMultiselectComponent } from './sucursal-multiselect.component';

const sucursales: OrdenSucursal[] = [
  { id: 1, name: 'Central', address: '', activa: true },
  { id: 2, name: 'Norte', address: '', activa: false },
  { id: 3, name: 'Sur', address: '' },
];

describe('SucursalMultiselectComponent', () => {
  let fixture: ComponentFixture<SucursalMultiselectComponent>;
  let component: SucursalMultiselectComponent;
  let control: FormControl<number[]>;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [SucursalMultiselectComponent] });
    fixture = TestBed.createComponent(SucursalMultiselectComponent);
    component = fixture.componentInstance;
    control = new FormControl<number[]>([1, 3], { nonNullable: true });
    component.sucursales = sucursales;
    component.control = control;
    component.inputId = 'ms';
    fixture.detectChanges();
  });

  it('con las activas marcadas (o nada) dice "Todas las activas"', () => {
    expect(component.label).toBe('Todas las activas');
    expect(component.allActiveSelected).toBeTrue();
    control.setValue([]);
    expect(component.label).toBe('Todas las activas');
  });

  it('marcar una inactiva cuenta las sucursales elegidas', () => {
    component.toggle(2);

    expect(control.value).toEqual([1, 3, 2]);
    expect(component.label).toBe('3 sucursales');
    expect(component.allActiveSelected).toBeFalse();
  });

  it('con una sola elegida muestra su nombre, y "(inactiva)" si lo es', () => {
    control.setValue([1]);
    expect(component.label).toBe('Central');
    control.setValue([2]);
    expect(component.label).toBe('Norte (inactiva)');
  });

  it('desmarcar quita el id; "Todas las activas" deja solo las activas', () => {
    control.setValue([1, 2, 3]);
    component.toggle(2);
    expect(control.value).toEqual([1, 3]);

    control.setValue([2]);
    component.selectAllActive();
    expect(control.value).toEqual([1, 3]);
  });

  it('el menu lista cada sucursal y marca las inactivas con un badge', () => {
    const toggle = (fixture.nativeElement as HTMLElement).querySelector('#ms') as HTMLButtonElement;
    toggle.click();
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Central');
    expect(text).toContain('Norte');
    expect(text).toContain('Inactiva');
  });
});
