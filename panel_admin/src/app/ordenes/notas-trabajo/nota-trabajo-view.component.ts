import { DatePipe } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { AuthService } from '../../core/service/auth.service';
import { extractApiError } from '../ordenes.errors';
import {
  AppNotaTrabajoDetail,
  NotaTrabajoUpdatePayload,
  OrdenInstalador,
  SALES_TYPE_INSTALACION,
} from '../ordenes.model';
import { OrdenesService } from '../ordenes.service';

/** Nota de trabajo: lectura y edicion in-situ. "Editar nota de trabajo" convierte
 * en inputs solo los campos operativos (codigo de garantia, instalador, salida del
 * vehiculo y observaciones); el resto queda en solo lectura. La ruta
 * `notas-trabajo/edit/:id` abre esta misma vista ya en modo edicion. */
@Component({
  selector: 'app-nota-trabajo-view',
  standalone: true,
  imports: [RouterLink, NgxDatatableModule, DatePipe, ReactiveFormsModule],
  templateUrl: './nota-trabajo-view.component.html',
})
export class NotaTrabajoViewComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private fb = inject(FormBuilder);
  private ordenesService = inject(OrdenesService);
  authService = inject(AuthService);

  nota: AppNotaTrabajoDetail | null = null;
  loading = true;
  errorMessage = '';

  editing = false;
  saving = false;
  submitted = false;
  saveError = '';
  savedMessage = '';
  instaladores: OrdenInstalador[] = [];
  form!: FormGroup;

  get isInstalacion(): boolean {
    return this.nota?.sales_type === SALES_TYPE_INSTALACION;
  }

  /** Badge de estado: verde = finalizado, ambar = en ejecucion. */
  get statusText(): string {
    return this.nota?.is_finalizada ? 'Finalizado' : 'En ejecución';
  }

  get statusClass(): string {
    return this.nota?.is_finalizada ? 'status-done' : 'status-progress';
  }

  get canEdit(): boolean {
    return (
      !!this.nota &&
      !this.nota.is_finalizada &&
      !this.nota.is_close &&
      this.authService.hasPermission('change_nota_trabajo')
    );
  }

  ngOnInit(): void {
    this.form = this.fb.group({
      // Reglas del modelo: maximo 12 caracteres y unico (el servidor valida el duplicado).
      codigo_garantia: ['', Validators.maxLength(12)],
      instaladar: [null as number | null],
      salida_vehiculo: [''],
      observaciones: [''],
    });
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.ordenesService.getNotaTrabajo(id).subscribe({
      next: (nota) => {
        this.nota = nota;
        this.loading = false;
        if (this.route.snapshot.data?.['edit'] && this.canEdit) {
          this.startEdit();
        }
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar la nota de trabajo.';
        this.loading = false;
      },
    });
  }

  /** Pasa los campos operativos a inputs, precargados con los valores guardados. */
  startEdit(): void {
    if (!this.nota || !this.canEdit) {
      return;
    }
    this.restoreForm();
    this.saveError = '';
    this.savedMessage = '';
    this.submitted = false;
    this.editing = true;
    if (this.nota.sucursal_id && this.instaladores.length === 0) {
      this.ordenesService
        .listInstaladores(this.nota.sucursal_id)
        .subscribe((rows) => (this.instaladores = rows));
    }
  }

  /** Descarta los cambios y restaura los valores originales. */
  cancelEdit(): void {
    this.restoreForm();
    this.editing = false;
    this.submitted = false;
    this.saveError = '';
    if (this.route.snapshot.data?.['edit'] && this.nota) {
      this.router.navigate(['/ordenes/notas-trabajo/view', this.nota.id]);
    }
  }

  private restoreForm(): void {
    if (!this.nota) {
      return;
    }
    this.form.reset({
      codigo_garantia: this.nota.codigo_garantia ?? '',
      instaladar: this.nota.instaladar,
      // USE_TZ=False en el backend: la fecha llega sin zona, sirve tal cual para datetime-local.
      salida_vehiculo: this.nota.salida_vehiculo ? this.nota.salida_vehiculo.slice(0, 16) : '',
      observaciones: this.nota.observaciones ?? '',
    });
  }

  save(): void {
    if (!this.editing || !this.nota) {
      return;
    }
    this.submitted = true;
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.value;
    const payload: NotaTrabajoUpdatePayload = {
      instaladar: value.instaladar,
      codigo_garantia: (value.codigo_garantia || '').trim(),
      salida_vehiculo: value.salida_vehiculo || null,
      observaciones: value.observaciones || '',
    };
    this.saving = true;
    this.saveError = '';
    this.ordenesService.updateNotaTrabajo(this.nota.id, payload).subscribe({
      next: (nota) => {
        this.nota = nota;
        this.saving = false;
        this.editing = false;
        this.submitted = false;
        this.savedMessage = 'Cambios guardados.';
        if (this.route.snapshot.data?.['edit']) {
          this.router.navigate(['/ordenes/notas-trabajo/view', nota.id]);
        }
      },
      error: (err) => {
        this.saving = false;
        this.saveError = extractApiError(err, 'No se pudo guardar la nota de trabajo.');
      },
    });
  }
}
