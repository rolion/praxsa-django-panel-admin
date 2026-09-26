import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { AppGroup, AppSucursal, AppUser } from '../users.model';
import { UsersService } from '../users.service';

@Component({
  selector: 'app-user-view',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './user-view.component.html',
})
export class UserViewComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private usersService = inject(UsersService);

  user?: AppUser;
  groupNames: string[] = [];
  sucursalNames: string[] = [];
  loading = true;
  errorMessage = '';

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    forkJoin({
      user: this.usersService.getUser(id),
      groups: this.usersService.listGroups(),
      sucursales: this.usersService.listSucursales(),
    }).subscribe({
      next: ({ user, groups, sucursales }) => {
        this.user = user;
        this.groupNames = groups
          .filter((group: AppGroup) => user.groups.includes(group.id))
          .map((group: AppGroup) => group.name);
        this.sucursalNames = sucursales
          .filter((sucursal: AppSucursal) => user.sucursales.includes(sucursal.id))
          .map((sucursal: AppSucursal) => sucursal.name);
        this.loading = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar el usuario.';
        this.loading = false;
      },
    });
  }
}
