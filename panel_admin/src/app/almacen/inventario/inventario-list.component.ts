import { Component, OnInit, TemplateRef, ViewChild, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { DatatableComponent, NgxDatatableModule } from '@swimlane/ngx-datatable';
import { AuthService } from '../../core/service/auth.service';
import { AppInventario } from '../almacen.model';
import { AlmacenService } from '../almacen.service';

/** Listado de Inventario, de solo consulta para ambos roles. La accion
 * "Gestionar" (modal, solo admin) edita unicamente los campos permitidos
 * por InventarioUpdateSerializer -- ver ADR-modulo-almacen-modelo-datos-
 * imagen-soft-delete punto 8 y DDR-modulo-almacen-listado-y-flujo-almacen. */
@Component({
  selector: 'app-inventario-list',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, NgxDatatableModule],
  templateUrl: './inventario-list.component.html',
})
export class InventarioListComponent implements OnInit {
  @ViewChild(DatatableComponent) table!: DatatableComponent;

  private fb = inject(FormBuilder);
  private modalService = inject(NgbModal);
  private almacenService = inject(AlmacenService);
  authService = inject(AuthService);

  data: AppInventario[] = [];
  rows: AppInventario[] = [];
  loadingIndicator = true;
  errorMessage = '';

  form!: FormGroup;
  formError = '';
  saving = false;
  managingId: number | null = null;

  ngOnInit(): void {
    this.form = this.fb.group({
      to_install: ['', Validators.required],
      installed: ['', Validators.required],
      precio_compra_mtr_lineal: ['', Validators.required],
      precio_venta_mtr_lineal: ['', Validators.required],
      nro_lote: [''],
    });
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

  openManage(row: AppInventario, content: TemplateRef<unknown>): void {
    this.managingId = row.id;
    this.formError = '';
    this.form.setValue({
      to_install: row.to_install,
      installed: row.installed,
      precio_compra_mtr_lineal: row.precio_compra_mtr_lineal,
      precio_venta_mtr_lineal: row.precio_venta_mtr_lineal,
      nro_lote: row.nro_lote || '',
    });
    this.modalService.open(content, { ariaLabelledBy: 'modal-basic-title' });
  }

  save(): void {
    if (this.form.invalid || this.managingId === null) {
      return;
    }
    this.saving = true;
    this.formError = '';
    this.almacenService.updateInventario(this.managingId, this.form.value).subscribe({
      next: () => {
        this.saving = false;
        this.modalService.dismissAll();
        this.load();
      },
      error: (err) => {
        this.saving = false;
        this.formError = err?.error?.to_install?.[0] || err?.error?.nro_lote?.[0] || 'No se pudo actualizar el inventario.';
      },
    });
  }
}
