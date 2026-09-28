import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthService } from '../../core/service/auth.service';
import { AppWindowFilm } from '../almacen.model';
import { AlmacenService } from '../almacen.service';

@Component({
  selector: 'app-lamina-view',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './lamina-view.component.html',
})
export class LaminaViewComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private almacenService = inject(AlmacenService);
  authService = inject(AuthService);

  lamina: AppWindowFilm | null = null;
  loading = true;
  errorMessage = '';

  get canManage(): boolean {
    return this.authService.hasGroup('admin');
  }

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.almacenService.getLamina(id).subscribe({
      next: (lamina) => {
        this.lamina = lamina;
        this.loading = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar la lamina.';
        this.loading = false;
      },
    });
  }
}
