import { Component, OnInit, TemplateRef, ViewChild, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { DatatableComponent, NgxDatatableModule } from '@swimlane/ngx-datatable';
import Swal from 'sweetalert2';
import { AppCarPart } from '../vehicles.model';
import { VehiclesService } from '../vehicles.service';

/** Listado de Items. Mismo patrón que BrandsListComponent (tabla, acciones,
 * búsqueda estilo advance-table, modal de un solo campo). */
@Component({
  selector: 'app-parts-list',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, NgxDatatableModule],
  templateUrl: './parts-list.component.html',
})
export class PartsListComponent implements OnInit {
  @ViewChild(DatatableComponent) table!: DatatableComponent;

  private vehiclesService = inject(VehiclesService);
  private modalService = inject(NgbModal);
  private fb = inject(FormBuilder);

  data: AppCarPart[] = [];
  rows: AppCarPart[] = [];
  loadingIndicator = true;
  errorMessage = '';
  form!: FormGroup;
  saving = false;
  formError = '';
  editingId: number | null = null;
  viewMode = false;

  ngOnInit(): void {
    this.form = this.fb.group({ name: ['', Validators.required] });
    this.load();
  }

  load(): void {
    this.loadingIndicator = true;
    this.vehiclesService.listParts().subscribe({
      next: (parts) => {
        this.data = parts;
        this.rows = parts;
        this.loadingIndicator = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar el listado de items.';
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

  openCreate(content: TemplateRef<unknown>): void {
    this.editingId = null;
    this.viewMode = false;
    this.formError = '';
    this.form.reset();
    this.modalService.open(content, { ariaLabelledBy: 'modal-basic-title' });
  }

  openEdit(part: AppCarPart, content: TemplateRef<unknown>): void {
    this.editingId = part.id;
    this.viewMode = false;
    this.formError = '';
    this.form.setValue({ name: part.name });
    this.modalService.open(content, { ariaLabelledBy: 'modal-basic-title' });
  }

  openView(part: AppCarPart, content: TemplateRef<unknown>): void {
    this.editingId = part.id;
    this.viewMode = true;
    this.formError = '';
    this.form.setValue({ name: part.name });
    this.modalService.open(content, { ariaLabelledBy: 'modal-basic-title' });
  }

  save(): void {
    if (this.form.invalid) {
      return;
    }
    this.saving = true;
    this.formError = '';
    const name = this.form.value.name;
    const request = this.editingId
      ? this.vehiclesService.updatePart(this.editingId, name)
      : this.vehiclesService.createPart(name);

    request.subscribe({
      next: () => {
        this.saving = false;
        this.modalService.dismissAll();
        this.load();
      },
      error: (err) => {
        this.saving = false;
        this.formError = err?.error?.name?.[0] || 'No se pudo guardar el item.';
      },
    });
  }

  deactivate(part: AppCarPart): void {
    Swal.fire({
      title: `¿Eliminar el item ${part.name}?`,
      text: 'El item quedará inactivo (no se borra físicamente).',
      showCancelButton: true,
      confirmButtonText: 'Eliminar',
      cancelButtonText: 'Cancelar',
    }).then((result) => {
      if (result.isConfirmed) {
        this.vehiclesService.togglePartActive(part.id, false).subscribe(() => this.load());
      }
    });
  }

  activate(part: AppCarPart): void {
    this.vehiclesService.togglePartActive(part.id, true).subscribe(() => this.load());
  }
}
