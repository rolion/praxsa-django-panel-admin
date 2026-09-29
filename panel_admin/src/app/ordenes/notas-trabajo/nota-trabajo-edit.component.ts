import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { extractApiError } from '../ordenes.errors';
import { AppNotaTrabajoDetail, NotaTrabajoUpdatePayload, OrdenInstalador } from '../ordenes.model';
import { OrdenesService } from '../ordenes.service';

/** Edicion operativa de una Nota de Trabajo: instalador, codigo de garantia,
 * salida del vehiculo y observaciones (ADR-modulo-ordenes-proforma-nota-
 * trabajo-api-y-calculo punto 9). */
@Component({
  selector: 'app-nota-trabajo-edit',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './nota-trabajo-edit.component.html',
})
export class NotaTrabajoEditComponent implements OnInit {
  private fb = inject(FormBuilder);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private ordenesService = inject(OrdenesService);

  form!: FormGroup;
  nota: AppNotaTrabajoDetail | null = null;
  instaladores: OrdenInstalador[] = [];
  loading = true;
  saving = false;
  submitted = false;
  errorMessage = '';

  ngOnInit(): void {
    this.form = this.fb.group({
      instaladar: [null as number | null],
      // Reglas del modelo: maximo 12 caracteres, unico (el servidor valida el duplicado).
      codigo_garantia: ['', Validators.maxLength(12)],
      salida_vehiculo: [''],
      observaciones: [''],
    });
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.ordenesService.getNotaTrabajo(id).subscribe({
      next: (nota) => {
        if (nota.is_finalizada || nota.is_close) {
          this.router.navigate(['/ordenes/notas-trabajo/view', nota.id]);
          return;
        }
        this.nota = nota;
        this.form.patchValue({
          instaladar: nota.instaladar,
          codigo_garantia: nota.codigo_garantia ?? '',
          // USE_TZ=False en el backend: la fecha llega sin zona, sirve tal cual para datetime-local.
          salida_vehiculo: nota.salida_vehiculo ? nota.salida_vehiculo.slice(0, 16) : '',
          observaciones: nota.observaciones ?? '',
        });
        if (nota.sucursal_id) {
          this.ordenesService.listInstaladores(nota.sucursal_id).subscribe((rows) => (this.instaladores = rows));
        }
        this.loading = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar la nota de trabajo.';
        this.loading = false;
      },
    });
  }

  save(): void {
    this.submitted = true;
    if (this.form.invalid || !this.nota) {
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
    this.errorMessage = '';
    this.ordenesService.updateNotaTrabajo(this.nota.id, payload).subscribe({
      next: (nota) => this.router.navigate(['/ordenes/notas-trabajo/view', nota.id]),
      error: (err) => {
        this.saving = false;
        this.errorMessage = extractApiError(err, 'No se pudo guardar la nota de trabajo.');
      },
    });
  }
}
