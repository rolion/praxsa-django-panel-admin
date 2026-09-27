import { Component, OnInit, ViewChild, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DatatableComponent, NgxDatatableModule } from '@swimlane/ngx-datatable';
import Swal from 'sweetalert2';
import { AuthService } from '../../core/service/auth.service';
import { AppInventario } from '../almacen.model';
import { AlmacenService } from '../almacen.service';

/** Listado de Inventario. Mismo patron de tabla/acciones/busqueda que
 * Lamina -- Ver/Crear/Editar('Gestionar')/Eliminar para admin, solo Ver
 * para almacen. Ver ADR-modulo-almacen-modelo-datos-imagen-soft-delete
 * (seccion Actualizacion): "Eliminar" puede fallar con 400 si la fila
 * todavia tiene metros disponibles para instalar. */
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
  loadingIndicator = true;
  errorMessage = '';

  ngOnInit(): void {
    this.load();
  }

  get canManage(): boolean {
    return this.authService.hasGroup('admin');
  }

  load(): void {
    this.loadingIndicator = true;
    this.almacenService.listInventario().subscribe({
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
