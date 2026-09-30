import { Component, OnInit, TemplateRef, ViewChild, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { DatatableComponent, NgxDatatableModule } from '@swimlane/ngx-datatable';
import Swal from 'sweetalert2';
import { AuthService } from '../../core/service/auth.service';
import { AppPrecioSucursal, AppSucursal, AppWindowFilm } from '../almacen.model';
import { AlmacenService } from '../almacen.service';

/** Listado de Precios por sucursal (override del precio del inventario para
 * una sucursal + lamina + ancho). Modal inline de crear/editar, igual al
 * patron de Bobinas (ver DDR-agrupacion-menu-instalador-precio-sucursal-menu-
 * y-pantallas). Eliminar borra la fila: la cotizacion vuelve al precio del
 * inventario. Solo `admin` ve los botones de escritura -- la barrera real son
 * los permisos Django del backend. */
@Component({
  selector: 'app-precios-sucursal-list',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, NgxDatatableModule],
  templateUrl: './precios-sucursal-list.component.html',
})
export class PreciosSucursalListComponent implements OnInit {
  @ViewChild(DatatableComponent) table!: DatatableComponent;

  private fb = inject(FormBuilder);
  private modalService = inject(NgbModal);
  private almacenService = inject(AlmacenService);
  authService = inject(AuthService);

  data: AppPrecioSucursal[] = [];
  rows: AppPrecioSucursal[] = [];
  sucursales: AppSucursal[] = [];
  laminas: AppWindowFilm[] = [];
  loadingIndicator = true;
  errorMessage = '';

  form!: FormGroup;
  formError = '';
  saving = false;
  submitted = false;
  editingId: number | null = null;

  ngOnInit(): void {
    this.form = this.fb.group({
      sucursal: [null, Validators.required],
      lamina: [null, Validators.required],
      width: ['', [Validators.required, Validators.min(0.01)]],
      precio_venta: ['', [Validators.required, Validators.min(0.01)]],
    });
    this.load();
  }

  get canManage(): boolean {
    return this.authService.hasGroup('admin');
  }

  load(): void {
    this.loadingIndicator = true;
    this.almacenService.listPreciosSucursal().subscribe({
      next: (precios) => {
        this.data = precios;
        this.rows = precios;
        this.loadingIndicator = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar el listado de precios por sucursal.';
        this.loadingIndicator = false;
      },
    });
  }

  filterDatatable(event: Event): void {
    const val = (event.target as HTMLInputElement).value.toLowerCase();
    this.rows = this.data.filter(
      (row) =>
        !val ||
        row.lamina_name.toLowerCase().indexOf(val) !== -1 ||
        row.sucursal_name.toLowerCase().indexOf(val) !== -1
    );
    if (this.table) {
      this.table.offset = 0;
    }
  }

  private loadOptions(): void {
    this.almacenService.listSucursales().subscribe((sucursales) => (this.sucursales = sucursales));
    this.almacenService.listLaminas().subscribe((laminas) => (this.laminas = laminas));
  }

  openCreate(content: TemplateRef<unknown>): void {
    this.editingId = null;
    this.submitted = false;
    this.formError = '';
    this.form.reset({ sucursal: null, lamina: null, width: '', precio_venta: '' });
    this.loadOptions();
    this.modalService.open(content, { ariaLabelledBy: 'modal-basic-title' });
  }

  openEdit(row: AppPrecioSucursal, content: TemplateRef<unknown>): void {
    this.editingId = row.id;
    this.submitted = false;
    this.formError = '';
    this.form.setValue({
      sucursal: row.sucursal,
      lamina: row.lamina,
      width: row.width,
      precio_venta: row.precio_venta,
    });
    this.loadOptions();
    this.modalService.open(content, { ariaLabelledBy: 'modal-basic-title' });
  }

  save(): void {
    this.submitted = true;
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving = true;
    this.formError = '';
    const payload = this.form.value;
    const request = this.editingId
      ? this.almacenService.updatePrecioSucursal(this.editingId, payload)
      : this.almacenService.createPrecioSucursal(payload);

    request.subscribe({
      next: () => {
        this.saving = false;
        this.modalService.dismissAll();
        this.load();
      },
      error: (err) => {
        this.saving = false;
        this.formError =
          err?.error?.non_field_errors?.[0] ||
          err?.error?.sucursal?.[0] ||
          err?.error?.lamina?.[0] ||
          err?.error?.width?.[0] ||
          err?.error?.precio_venta?.[0] ||
          err?.error?.detail ||
          'No se pudo guardar el precio.';
      },
    });
  }

  remove(row: AppPrecioSucursal): void {
    Swal.fire({
      title: `¿Eliminar el precio de ${row.lamina_name} (${row.width}) en ${row.sucursal_name}?`,
      text: 'Se borra el precio de esta sucursal: la cotización volverá a usar el precio del inventario. Las proformas ya emitidas no cambian.',
      showCancelButton: true,
      confirmButtonText: 'Eliminar',
      cancelButtonText: 'Cancelar',
    }).then((result) => {
      if (result.isConfirmed) {
        this.almacenService.deletePrecioSucursal(row.id).subscribe(() => this.load());
      }
    });
  }
}
