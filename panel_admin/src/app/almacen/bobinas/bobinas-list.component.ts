import { Component, OnInit, TemplateRef, ViewChild, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { DatatableComponent, NgxDatatableModule } from '@swimlane/ngx-datatable';
import Swal from 'sweetalert2';
import { AuthService } from '../../core/service/auth.service';
import { AppWindowFilm, AppWindowFilmReel } from '../almacen.model';
import { AlmacenService } from '../almacen.service';

/** Listado de Bobinas. Sin imagen ni pantalla de detalle propia -- modal
 * inline igual al patron de Marca/Item de Vehiculos (ver DDR-modulo-
 * almacen-listado-y-flujo-almacen). */
@Component({
  selector: 'app-bobinas-list',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, NgxDatatableModule],
  templateUrl: './bobinas-list.component.html',
})
export class BobinasListComponent implements OnInit {
  @ViewChild(DatatableComponent) table!: DatatableComponent;

  private fb = inject(FormBuilder);
  private modalService = inject(NgbModal);
  private almacenService = inject(AlmacenService);
  authService = inject(AuthService);

  data: AppWindowFilmReel[] = [];
  rows: AppWindowFilmReel[] = [];
  laminas: AppWindowFilm[] = [];
  loadingIndicator = true;
  errorMessage = '';

  form!: FormGroup;
  formError = '';
  saving = false;
  submitted = false;
  editingId: number | null = null;
  viewMode = false;

  ngOnInit(): void {
    this.form = this.fb.group({
      window_film: [null, Validators.required],
      width: ['', Validators.required],
      length: ['', Validators.required],
      price: ['', Validators.required],
    });
    this.load();
  }

  get canManage(): boolean {
    return this.authService.hasGroup('admin');
  }

  load(): void {
    this.loadingIndicator = true;
    this.almacenService.listBobinas().subscribe({
      next: (bobinas) => {
        this.data = bobinas;
        this.rows = bobinas;
        this.loadingIndicator = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar el listado de bobinas.';
        this.loadingIndicator = false;
      },
    });
  }

  filterDatatable(event: Event): void {
    const val = (event.target as HTMLInputElement).value.toLowerCase();
    this.rows = this.data.filter(
      (row) => !val || row.window_film_name.toLowerCase().indexOf(val) !== -1
    );
    if (this.table) {
      this.table.offset = 0;
    }
  }

  openCreate(content: TemplateRef<unknown>): void {
    this.editingId = null;
    this.viewMode = false;
    this.submitted = false;
    this.formError = '';
    this.form.reset();
    this.almacenService.listLaminas().subscribe((laminas) => (this.laminas = laminas));
    this.modalService.open(content, { ariaLabelledBy: 'modal-basic-title' });
  }

  openEdit(row: AppWindowFilmReel, content: TemplateRef<unknown>): void {
    this.editingId = row.id;
    this.viewMode = false;
    this.submitted = false;
    this.formError = '';
    this.almacenService.listLaminas().subscribe((laminas) => (this.laminas = laminas));
    this.form.setValue({
      window_film: row.window_film,
      width: row.width,
      length: row.length,
      price: row.price,
    });
    this.modalService.open(content, { ariaLabelledBy: 'modal-basic-title' });
  }

  openView(row: AppWindowFilmReel, content: TemplateRef<unknown>): void {
    this.editingId = row.id;
    this.viewMode = true;
    this.submitted = false;
    this.formError = '';
    this.almacenService.listLaminas().subscribe((laminas) => (this.laminas = laminas));
    this.form.setValue({
      window_film: row.window_film,
      width: row.width,
      length: row.length,
      price: row.price,
    });
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
    const { window_film, width, length, price } = this.form.value;
    const request = this.editingId
      ? this.almacenService.updateBobina(this.editingId, window_film, width, length, price)
      : this.almacenService.createBobina(window_film, width, length, price);

    request.subscribe({
      next: () => {
        this.saving = false;
        this.modalService.dismissAll();
        this.load();
      },
      error: (err) => {
        this.saving = false;
        this.formError =
          err?.error?.window_film?.[0] || err?.error?.width?.[0] || err?.error?.length?.[0] ||
          err?.error?.price?.[0] || 'No se pudo guardar la bobina.';
      },
    });
  }

  deactivate(reel: AppWindowFilmReel): void {
    Swal.fire({
      title: `¿Eliminar la bobina de ${reel.window_film_name}?`,
      text: 'La bobina quedara inactiva (no se borra fisicamente).',
      showCancelButton: true,
      confirmButtonText: 'Eliminar',
      cancelButtonText: 'Cancelar',
    }).then((result) => {
      if (result.isConfirmed) {
        this.almacenService.toggleBobinaActive(reel.id, false).subscribe(() => this.load());
      }
    });
  }

  activate(reel: AppWindowFilmReel): void {
    this.almacenService.toggleBobinaActive(reel.id, true).subscribe(() => this.load());
  }
}
