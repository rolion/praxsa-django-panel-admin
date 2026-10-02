import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthService } from '../../core/service/auth.service';
import { AppInventario } from '../almacen.model';
import { AlmacenService } from '../almacen.service';

@Component({
  selector: 'app-inventario-view',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './inventario-view.component.html',
})
export class InventarioViewComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private almacenService = inject(AlmacenService);
  authService = inject(AuthService);

  inventario: AppInventario | null = null;
  loading = true;
  errorMessage = '';

  /** Gestionar: permiso `change_inventario` y sucursal de la fila activa. */
  get canManage(): boolean {
    return this.authService.hasPermission('change_inventario') && this.inventario?.sucursal_activa !== false;
  }

  get sucursalInactiva(): boolean {
    return this.inventario?.sucursal_activa === false;
  }

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.almacenService.getInventario(id).subscribe({
      next: (inventario) => {
        this.inventario = inventario;
        this.loading = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar el inventario.';
        this.loading = false;
      },
    });
  }
}
