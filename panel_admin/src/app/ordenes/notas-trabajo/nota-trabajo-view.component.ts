import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthService } from '../../core/service/auth.service';
import { AppNotaTrabajoDetail } from '../ordenes.model';
import { OrdenesService } from '../ordenes.service';

@Component({
  selector: 'app-nota-trabajo-view',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './nota-trabajo-view.component.html',
})
export class NotaTrabajoViewComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private ordenesService = inject(OrdenesService);
  authService = inject(AuthService);

  nota: AppNotaTrabajoDetail | null = null;
  loading = true;
  errorMessage = '';

  get canEdit(): boolean {
    return (
      !!this.nota &&
      !this.nota.is_finalizada &&
      !this.nota.is_close &&
      this.authService.hasPermission('change_nota_trabajo')
    );
  }

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.ordenesService.getNotaTrabajo(id).subscribe({
      next: (nota) => {
        this.nota = nota;
        this.loading = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar la nota de trabajo.';
        this.loading = false;
      },
    });
  }
}
