import { Component, OnInit, TemplateRef, ViewChild, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { DatatableComponent, NgxDatatableModule } from '@swimlane/ngx-datatable';
import Swal from 'sweetalert2';
import { AppCarBrand } from '../vehicles.model';
import { VehiclesService } from '../vehicles.service';

/** Listado de Marcas. Tabla, acciones y confirmación de borrado replican
 * exactamente el patrón de "Credenciales" (users-list.component). La
 * búsqueda reutiliza el patrón ya existente en advance-table.component
 * (markup + filtrado client-side con reset de página), en vez de un
 * componente nuevo -- ver DDR-modulo-vehiculos, sección "Corrección". */
@Component({
  selector: 'app-brands-list',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, NgxDatatableModule],
  templateUrl: './brands-list.component.html',
})
export class BrandsListComponent implements OnInit {
  @ViewChild(DatatableComponent) table!: DatatableComponent;

  private vehiclesService = inject(VehiclesService);
  private modalService = inject(NgbModal);
  private fb = inject(FormBuilder);

  data: AppCarBrand[] = [];
  rows: AppCarBrand[] = [];
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
    this.vehiclesService.listBrands().subscribe({
      next: (brands) => {
        this.data = brands;
        this.rows = brands;
        this.loadingIndicator = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar el listado de marcas.';
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

  openEdit(brand: AppCarBrand, content: TemplateRef<unknown>): void {
    this.editingId = brand.id;
    this.viewMode = false;
    this.formError = '';
    this.form.setValue({ name: brand.name });
    this.modalService.open(content, { ariaLabelledBy: 'modal-basic-title' });
  }

  openView(brand: AppCarBrand, content: TemplateRef<unknown>): void {
    this.editingId = brand.id;
    this.viewMode = true;
    this.formError = '';
    this.form.setValue({ name: brand.name });
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
      ? this.vehiclesService.updateBrand(this.editingId, name)
      : this.vehiclesService.createBrand(name);

    request.subscribe({
      next: () => {
        this.saving = false;
        this.modalService.dismissAll();
        this.load();
      },
      error: (err) => {
        this.saving = false;
        this.formError = err?.error?.name?.[0] || 'No se pudo guardar la marca.';
      },
    });
  }

  deactivate(brand: AppCarBrand): void {
    Swal.fire({
      title: `¿Eliminar la marca ${brand.name}?`,
      text: 'La marca quedará inactiva (no se borra físicamente).',
      showCancelButton: true,
      confirmButtonText: 'Eliminar',
      cancelButtonText: 'Cancelar',
    }).then((result) => {
      if (result.isConfirmed) {
        this.vehiclesService.toggleBrandActive(brand.id, false).subscribe(() => this.load());
      }
    });
  }

  activate(brand: AppCarBrand): void {
    this.vehiclesService.toggleBrandActive(brand.id, true).subscribe(() => this.load());
  }
}
