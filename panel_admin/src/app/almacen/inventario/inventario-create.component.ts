import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AppSucursal, AppWindowFilmReel } from '../almacen.model';
import { AlmacenService } from '../almacen.service';

@Component({
  selector: 'app-inventario-create',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './inventario-create.component.html',
})
export class InventarioCreateComponent implements OnInit {
  private fb = inject(FormBuilder);
  private router = inject(Router);
  private almacenService = inject(AlmacenService);

  form!: FormGroup;
  sucursales: AppSucursal[] = [];
  bobinas: AppWindowFilmReel[] = [];
  saving = false;
  errorMessage = '';

  ngOnInit(): void {
    this.form = this.fb.group({
      sucursal: [null, Validators.required],
      bobina: [null, Validators.required],
      quantity: ['', Validators.required],
      to_install: ['', Validators.required],
      precio_compra_mtr_lineal: ['', Validators.required],
      precio_venta_mtr_lineal: ['', Validators.required],
      // nro_lote es obligatorio (corregido tras feedback directo del
      // usuario -- el panel anterior ya lo exigia en la practica) y
      // espeja las mismas reglas que el modelo backend: alfanumerico,
      // maximo 15 caracteres (ver ADR-modulo-almacen-modelo-datos-imagen-
      // soft-delete, "Correccion (2026-09-27)").
      nro_lote: ['', [Validators.required, Validators.pattern(/^[0-9a-zA-Z]*$/), Validators.maxLength(15)]],
    });
    this.almacenService.listSucursales().subscribe((sucursales) => (this.sucursales = sucursales));
    this.almacenService.listBobinas().subscribe((bobinas) => (this.bobinas = bobinas));
  }

  save(): void {
    if (this.form.invalid) {
      return;
    }
    this.saving = true;
    this.errorMessage = '';
    this.almacenService.createInventario(this.form.value).subscribe({
      next: (inv) => this.router.navigate(['/almacen/inventario/view', inv.id]),
      error: (err) => {
        this.saving = false;
        this.errorMessage =
          err?.error?.sucursal?.[0] || err?.error?.bobina?.[0] || err?.error?.quantity?.[0] ||
          err?.error?.to_install?.[0] || err?.error?.precio_compra_mtr_lineal?.[0] ||
          err?.error?.precio_venta_mtr_lineal?.[0] || err?.error?.nro_lote?.[0] ||
          err?.error?.numero_referencia?.[0] || 'No se pudo crear el inventario.';
      },
    });
  }
}
