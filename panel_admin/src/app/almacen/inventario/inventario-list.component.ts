import { Component, OnInit, ViewChild, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DatatableComponent, NgxDatatableModule } from '@swimlane/ngx-datatable';
import Swal from 'sweetalert2';
import { AuthService } from '../../core/service/auth.service';
import { AppInventario, AppSucursal, AppWindowFilm, sucursalLabel } from '../almacen.model';
import { AlmacenService } from '../almacen.service';

/** Listado de Inventario. Mismo patron de tabla/acciones/busqueda que
 * Lamina. El servidor devuelve solo el inventario de las sucursales asignadas
 * al usuario (sin excepcion de grupo; solo el superusuario ve todas) y aplica
 * los filtros de lamina y sucursal; con una sola sucursal el selector queda
 * fijo. Las filas de una sucursal inactiva se ven con un badge pero sin
 * acciones de escritura. Crear/Editar/Eliminar se muestran segun los permisos
 * Django del usuario y la sucursal de la fila (la barrera real es el backend), ver
 * DDR-inventario-alcance-sucursal-django-admin-sucursales-inactivas-y-filtro-reportes,
 * DDR-almacen-permisos-sucursal-filtros-filtros-y-selector-sucursal y
 * ADR-almacen-permisos-sucursal-filtros-alcance-inventario. "Eliminar" puede
 * fallar con 400 si la fila todavia tiene metros disponibles para instalar
 * (ADR-modulo-almacen-modelo-datos-imagen-soft-delete). */
@Component({
  selector: 'app-inventario-list',
  standalone: true,
  imports: [RouterLink, NgxDatatableModule],
  templateUrl: './inventario-list.component.html',
})
export class InventarioListComponent implements OnInit {
  @ViewChild(DatatableComponent) table!: DatatableComponent;

  private almacenService = inject(AlmacenService);
  authService = inject(AuthService);

  data: AppInventario[] = [];
  rows: AppInventario[] = [];
  sucursales: AppSucursal[] = [];
  laminas: AppWindowFilm[] = [];
  selectedSucursal: number | null = null;
  selectedLamina: number | null = null;
  sucursalesLoaded = false;
  loadingIndicator = true;
  errorMessage = '';

  ngOnInit(): void {
    this.almacenService.listLaminas().subscribe((laminas) => (this.laminas = laminas));
    this.almacenService.listSucursalesAlcance().subscribe({
      next: (sucursales) => {
        this.sucursales = sucursales;
        this.sucursalesLoaded = true;
        if (sucursales.length === 1) {
          this.selectedSucursal = sucursales[0].id;
        }
        this.load();
      },
      error: () => {
        this.sucursalesLoaded = true;
        this.load();
      },
    });
  }

  /** Con una sola sucursal en alcance el selector queda fijo y deshabilitado. */
  get sucursalLocked(): boolean {
    return this.sucursales.length === 1;
  }

  get withoutSucursales(): boolean {
    return this.sucursalesLoaded && this.sucursales.length === 0;
  }

  readonly sucursalLabel = sucursalLabel;

  get sucursalPlaceholder(): string {
    return 'Todas mis sucursales';
  }

  /** Hay al menos una sucursal activa donde agregar inventario. */
  get hasActiveSucursal(): boolean {
    return this.sucursales.some((sucursal) => sucursal.activa !== false);
  }

  /** Tiene sucursales, pero todas inactivas: puede consultar, no agregar. */
  get onlyInactiveSucursales(): boolean {
    return this.sucursalesLoaded && this.sucursales.length > 0 && !this.hasActiveSucursal;
  }

  get canCreate(): boolean {
    return this.authService.hasPermission('add_inventario') && !this.withoutSucursales && !this.onlyInactiveSucursales;
  }

  get canEdit(): boolean {
    return this.authService.hasPermission('change_inventario');
  }

  /** Editar/Eliminar/Activar: permiso y sucursal de la fila activa. */
  canEditRow(row: AppInventario): boolean {
    return this.canEdit && row.sucursal_activa !== false;
  }

  private static parseId(event: Event): number | null {
    const value = (event.target as HTMLSelectElement).value;
    return value ? Number(value) : null;
  }

  onSucursalChange(event: Event): void {
    this.selectedSucursal = InventarioListComponent.parseId(event);
    this.load();
  }

  onLaminaChange(event: Event): void {
    this.selectedLamina = InventarioListComponent.parseId(event);
    this.load();
  }

  load(): void {
    this.loadingIndicator = true;
    this.almacenService
      .listInventario({ sucursal: this.selectedSucursal, windowFilm: this.selectedLamina })
      .subscribe({
        next: (rows) => {
          this.data = rows;
          this.rows = rows;
          this.loadingIndicator = false;
        },
        error: () => {
          this.errorMessage = 'No se pudo cargar el inventario.';
          this.loadingIndicator = false;
        },
      });
    if (this.table) {
      this.table.offset = 0;
    }
  }

  filterDatatable(event: Event): void {
    const val = (event.target as HTMLInputElement).value.toLowerCase();
    this.rows = this.data.filter(
      (row) =>
        !val ||
        row.window_film_name.toLowerCase().indexOf(val) !== -1 ||
        row.sucursal_name.toLowerCase().indexOf(val) !== -1 ||
        (row.nro_lote || '').toLowerCase().indexOf(val) !== -1
    );
    if (this.table) {
      this.table.offset = 0;
    }
  }

  deactivate(row: AppInventario): void {
    Swal.fire({
      title: '¿Eliminar este inventario?',
      text: 'El inventario quedará inactivo (no se borra físicamente).',
      showCancelButton: true,
      confirmButtonText: 'Eliminar',
      cancelButtonText: 'Cancelar',
    }).then((result) => {
      if (result.isConfirmed) {
        this.almacenService.toggleInventarioActive(row.id, false).subscribe({
          next: () => this.load(),
          error: (err) => {
            const message =
              err?.error?.detail || 'No se pudo eliminar el inventario.';
            Swal.fire({ title: 'No se pudo eliminar', text: message, icon: 'error' });
          },
        });
      }
    });
  }

  activate(row: AppInventario): void {
    this.almacenService.toggleInventarioActive(row.id, true).subscribe(() => this.load());
  }
}
