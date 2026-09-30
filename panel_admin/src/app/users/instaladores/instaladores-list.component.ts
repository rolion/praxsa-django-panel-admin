import { Component, OnInit, TemplateRef, ViewChild, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgSelectModule } from '@ng-select/ng-select';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { DatatableComponent, NgxDatatableModule } from '@swimlane/ngx-datatable';
import Swal from 'sweetalert2';
import { AuthService } from '../../core/service/auth.service';
import { AppInstalador, AppSucursal } from '../users.model';
import { UsersService } from '../users.service';

/** Listado de Instaladores (personal de instalacion de las sucursales). Modal
 * inline de crear/editar, igual al patron de Bobinas/Marcas (ver DDR-
 * agrupacion-menu-instalador-precio-sucursal-menu-y-pantallas). "Eliminar"
 * desactiva (borrado logico); solo `admin` ve los botones de escritura -- la
 * barrera real son los permisos Django del backend. */
@Component({
  selector: 'app-instaladores-list',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, NgxDatatableModule, NgSelectModule],
  templateUrl: './instaladores-list.component.html',
})
export class InstaladoresListComponent implements OnInit {
  @ViewChild(DatatableComponent) table!: DatatableComponent;

  private fb = inject(FormBuilder);
  private modalService = inject(NgbModal);
  private usersService = inject(UsersService);
  authService = inject(AuthService);

  data: AppInstalador[] = [];
  rows: AppInstalador[] = [];
  sucursales: AppSucursal[] = [];
  loadingIndicator = true;
  errorMessage = '';

  form!: FormGroup;
  formError = '';
  saving = false;
  submitted = false;
  editingId: number | null = null;

  ngOnInit(): void {
    this.form = this.fb.group({
      name: ['', [Validators.required, Validators.maxLength(20)]],
      address: ['', [Validators.required, Validators.maxLength(400)]],
      phonenumber: ['', [Validators.required, Validators.pattern(/^\+?\d{7,11}$/)]],
      sucursal: [[] as number[], Validators.required],
    });
    this.load();
  }

  get canManage(): boolean {
    return this.authService.hasGroup('admin');
  }

  load(): void {
    this.loadingIndicator = true;
    this.usersService.listInstaladores().subscribe({
      next: (instaladores) => {
        this.data = instaladores;
        this.rows = instaladores;
        this.loadingIndicator = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar el listado de instaladores.';
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

  private loadSucursales(): void {
    this.usersService.listSucursales().subscribe((sucursales) => (this.sucursales = sucursales));
  }

  openCreate(content: TemplateRef<unknown>): void {
    this.editingId = null;
    this.submitted = false;
    this.formError = '';
    this.form.reset({ name: '', address: '', phonenumber: '', sucursal: [] });
    this.loadSucursales();
    this.modalService.open(content, { ariaLabelledBy: 'modal-basic-title' });
  }

  openEdit(row: AppInstalador, content: TemplateRef<unknown>): void {
    this.editingId = row.id;
    this.submitted = false;
    this.formError = '';
    this.form.setValue({
      name: row.name,
      address: row.address,
      phonenumber: row.phonenumber,
      sucursal: row.sucursal,
    });
    this.loadSucursales();
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
      ? this.usersService.updateInstalador(this.editingId, payload)
      : this.usersService.createInstalador(payload);

    request.subscribe({
      next: () => {
        this.saving = false;
        this.modalService.dismissAll();
        this.load();
      },
      error: (err) => {
        this.saving = false;
        this.formError =
          err?.error?.name?.[0] ||
          err?.error?.address?.[0] ||
          err?.error?.phonenumber?.[0] ||
          err?.error?.sucursal?.[0] ||
          err?.error?.detail ||
          'No se pudo guardar el instalador.';
      },
    });
  }

  deactivate(row: AppInstalador): void {
    Swal.fire({
      title: `¿Eliminar al instalador ${row.name}?`,
      text: 'Quedará inactivo: ya no se podrá asignar a notas de trabajo, pero las notas existentes lo conservan.',
      showCancelButton: true,
      confirmButtonText: 'Eliminar',
      cancelButtonText: 'Cancelar',
    }).then((result) => {
      if (result.isConfirmed) {
        this.usersService.toggleInstaladorActive(row.id, false).subscribe(() => this.load());
      }
    });
  }
}
