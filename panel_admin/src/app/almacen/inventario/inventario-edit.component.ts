import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AlmacenService } from '../almacen.service';

/** "Gestionar" un Inventario existente -- migrado del modal inline (v1) a
 * pagina propia, ahora que Inventario tiene Ver/Crear/Eliminar ademas de
 * esto (ver DDR-modulo-almacen-listado-y-flujo-almacen, seccion
 * Actualizacion). Mismos 5 campos editables de siempre, sin cambios de
 * contrato. */
@Component({
  selector: 'app-inventario-edit',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './inventario-edit.component.html',
})
export class InventarioEditComponent implements OnInit {
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private almacenService = inject(AlmacenService);

  inventarioId!: number;
  form!: FormGroup;
  loading = true;
  saving = false;
  submitted = false;
  errorMessage = '';

  ngOnInit(): void {
    this.inventarioId = Number(this.route.snapshot.paramMap.get('id'));
    this.form = this.fb.group({
      to_install: ['', Validators.required],
      installed: ['', Validators.required],
      precio_compra_mtr_lineal: ['', Validators.required],
      precio_venta_mtr_lineal: ['', Validators.required],
      nro_lote: [''],
    });

    this.almacenService.getInventario(this.inventarioId).subscribe({
      next: (inv) => {
        this.form.patchValue({
          to_install: inv.to_install,
          installed: inv.installed,
          precio_compra_mtr_lineal: inv.precio_compra_mtr_lineal,
          precio_venta_mtr_lineal: inv.precio_venta_mtr_lineal,
          nro_lote: inv.nro_lote || '',
        });
        this.loading = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar el inventario.';
        this.loading = false;
      },
    });
  }

  save(): void {
    this.submitted = true;
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving = true;
    this.errorMessage = '';
    this.almacenService.updateInventario(this.inventarioId, this.form.value).subscribe({
      next: () => this.router.navigate(['/almacen/inventario/view', this.inventarioId]),
      error: (err) => {
        this.saving = false;
        this.errorMessage =
          err?.error?.to_install?.[0] || err?.error?.nro_lote?.[0] || 'No se pudo guardar el inventario.';
      },
    });
  }
}
