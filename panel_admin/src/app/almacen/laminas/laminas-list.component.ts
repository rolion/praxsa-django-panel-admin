import { Component, OnInit, ViewChild, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DatatableComponent, NgxDatatableModule } from '@swimlane/ngx-datatable';
import Swal from 'sweetalert2';
import { AuthService } from '../../core/service/auth.service';
import { AppWindowFilm } from '../almacen.model';
import { AlmacenService } from '../almacen.service';

/** Listado de Laminas. Mismo patron de tabla/acciones/busqueda que Marcas/
 * Modelos de Vehiculos, con miniatura de imagen. Las acciones de escritura
 * se ocultan para el rol `almacen` (ver DDR-modulo-almacen-listado-y-flujo-
 * almacen) -- la barrera real es el backend (ADR-modulo-almacen-permisos-
 * rol-frontend). */
@Component({
  selector: 'app-laminas-list',
  standalone: true,
  imports: [RouterLink, NgxDatatableModule],
  templateUrl: './laminas-list.component.html',
})
export class LaminasListComponent implements OnInit {
  @ViewChild(DatatableComponent) table!: DatatableComponent;

  private almacenService = inject(AlmacenService);
  authService = inject(AuthService);

  data: AppWindowFilm[] = [];
  rows: AppWindowFilm[] = [];
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
    this.almacenService.listLaminas().subscribe({
      next: (laminas) => {
        this.data = laminas;
        this.rows = laminas;
        this.loadingIndicator = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar el listado de laminas.';
        this.loadingIndicator = false;
      },
    });
  }

  filterDatatable(event: Event): void {
    const val = (event.target as HTMLInputElement).value.toLowerCase();
    this.rows = this.data.filter((row) => !val || row.name.toLowerCase().indexOf(val) !== -1);
    if (this.table) {
      this.table.offset = 0;
    }
  }

  deactivate(lamina: AppWindowFilm): void {
    Swal.fire({
      title: `¿Eliminar la lamina ${lamina.name}?`,
      text: 'La lamina quedara inactiva (no se borra fisicamente).',
      showCancelButton: true,
      confirmButtonText: 'Eliminar',
      cancelButtonText: 'Cancelar',
    }).then((result) => {
      if (result.isConfirmed) {
        this.almacenService.toggleLaminaActive(lamina.id, false).subscribe(() => this.load());
      }
    });
  }

  activate(lamina: AppWindowFilm): void {
    this.almacenService.toggleLaminaActive(lamina.id, true).subscribe(() => this.load());
  }
}
