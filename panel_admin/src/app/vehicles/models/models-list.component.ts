import { Component, OnInit, ViewChild, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DatatableComponent, NgxDatatableModule } from '@swimlane/ngx-datatable';
import Swal from 'sweetalert2';
import { AppCarModel } from '../vehicles.model';
import { VehiclesService } from '../vehicles.service';

/** Listado de Modelos. Mismo patrón de tabla/acciones/búsqueda que Marcas e
 * Items, con la columna adicional de imagen (thumbnail o placeholder). */
@Component({
  selector: 'app-models-list',
  standalone: true,
  imports: [RouterLink, NgxDatatableModule],
  templateUrl: './models-list.component.html',
})
export class ModelsListComponent implements OnInit {
  @ViewChild(DatatableComponent) table!: DatatableComponent;

  private vehiclesService = inject(VehiclesService);

  data: AppCarModel[] = [];
  rows: AppCarModel[] = [];
  loadingIndicator = true;
  errorMessage = '';

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loadingIndicator = true;
    this.vehiclesService.listModels().subscribe({
      next: (models) => {
        this.data = models;
        this.rows = models;
        this.loadingIndicator = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar el listado de modelos.';
        this.loadingIndicator = false;
      },
    });
  }

  filterDatatable(event: Event): void {
    const val = (event.target as HTMLInputElement).value.toLowerCase();
    this.rows = this.data.filter(
      (row) =>
        !val ||
        row.name.toLowerCase().indexOf(val) !== -1 ||
        row.car_brand_name.toLowerCase().indexOf(val) !== -1
    );
    if (this.table) {
      this.table.offset = 0;
    }
  }

  deactivate(model: AppCarModel): void {
    Swal.fire({
      title: `¿Eliminar el modelo ${model.name}?`,
      text: 'El modelo quedará inactivo (no se borra físicamente).',
      showCancelButton: true,
      confirmButtonText: 'Eliminar',
      cancelButtonText: 'Cancelar',
    }).then((result) => {
      if (result.isConfirmed) {
        this.vehiclesService.toggleModelActive(model.id, false).subscribe(() => this.load());
      }
    });
  }

  activate(model: AppCarModel): void {
    this.vehiclesService.toggleModelActive(model.id, true).subscribe(() => this.load());
  }
}
