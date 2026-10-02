import { Component, Input } from '@angular/core';
import { FormControl } from '@angular/forms';
import { NgbDropdown, NgbDropdownMenu, NgbDropdownToggle } from '@ng-bootstrap/ng-bootstrap';
import { OrdenSucursal } from '../ordenes/ordenes.model';

/** Filtro de sucursal de los reportes: menu desplegable con casillas (multiselect). Por defecto
 * quedan marcadas las sucursales ACTIVAS; las inactivas se pueden marcar para consultar su
 * historico. Una seleccion vacia equivale a "todas las activas" en el servidor. Ver
 * DDR-inventario-alcance-sucursal-django-admin-sucursales-inactivas-y-filtro-reportes y
 * ADR-...-filtro-multisucursal-reportes. */
@Component({
  selector: 'app-sucursal-multiselect',
  standalone: true,
  imports: [NgbDropdown, NgbDropdownToggle, NgbDropdownMenu],
  template: `
    <div ngbDropdown class="d-block sucursal-multiselect" [autoClose]="'outside'">
      <button type="button" ngbDropdownToggle class="form-select form-control text-start" [id]="inputId">
        {{ label }}
      </button>
      <div ngbDropdownMenu class="p-2 w-100">
        <div class="form-check">
          <input class="form-check-input" type="checkbox" [id]="inputId + '-todas'"
            [checked]="allActiveSelected" (change)="selectAllActive()" />
          <label class="form-check-label fw-bold" [for]="inputId + '-todas'">Todas las activas</label>
        </div>
        @for (sucursal of sucursales; track sucursal.id) {
          <div class="form-check">
            <input class="form-check-input" type="checkbox" [id]="inputId + '-' + sucursal.id"
              [checked]="isSelected(sucursal.id)" (change)="toggle(sucursal.id)" />
            <label class="form-check-label" [for]="inputId + '-' + sucursal.id">
              {{ sucursal.name }}
              @if (sucursal.activa === false) {
                <span class="badge bg-warning text-dark ms-1">Inactiva</span>
              }
            </label>
          </div>
        }
      </div>
    </div>
  `,
})
export class SucursalMultiselectComponent {
  @Input({ required: true }) sucursales: OrdenSucursal[] = [];
  @Input({ required: true }) control!: FormControl<number[]>;
  @Input() inputId = 'sucursal-multiselect';

  private get activeIds(): number[] {
    return this.sucursales.filter((sucursal) => sucursal.activa !== false).map((sucursal) => sucursal.id);
  }

  private get selected(): number[] {
    return this.control.value ?? [];
  }

  isSelected(id: number): boolean {
    return this.selected.includes(id);
  }

  /** Solo las activas marcadas (o seleccion vacia, que el servidor trata igual). */
  get allActiveSelected(): boolean {
    const selected = this.selected;
    const active = this.activeIds;
    return (
      selected.length === 0 ||
      (selected.length === active.length && active.every((id) => selected.includes(id)))
    );
  }

  get label(): string {
    if (this.allActiveSelected) {
      return 'Todas las activas';
    }
    const chosen = this.sucursales.filter((sucursal) => this.isSelected(sucursal.id));
    if (chosen.length === 1) {
      return chosen[0].activa === false ? `${chosen[0].name} (inactiva)` : chosen[0].name;
    }
    return `${chosen.length} sucursales`;
  }

  toggle(id: number): void {
    const next = this.isSelected(id) ? this.selected.filter((value) => value !== id) : [...this.selected, id];
    this.control.setValue(next);
    this.control.markAsDirty();
  }

  selectAllActive(): void {
    this.control.setValue(this.activeIds);
    this.control.markAsDirty();
  }
}
