import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { AppGroup, AppSucursal, AppUser } from '../users.model';
import { UsersService } from '../users.service';

const MAX_CHIPS = 3;

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
  showAllGroups = false;
  showAllSucursales = false;
  loading = true;
  errorMessage = '';

  get fullName(): string {
    if (!this.user) {
      return '';
    }
    const name = `${this.user.first_name} ${this.user.last_name}`.trim();
    return name || this.user.username;
  }

  get visibleGroups(): string[] {
    return this.showAllGroups ? this.groupNames : this.groupNames.slice(0, MAX_CHIPS);
  }

  get hiddenGroupCount(): number {
    return Math.max(this.groupNames.length - MAX_CHIPS, 0);
  }

  get visibleSucursales(): string[] {
    return this.showAllSucursales ? this.sucursalNames : this.sucursalNames.slice(0, MAX_CHIPS);
  }

  get hiddenSucursalCount(): number {
    return Math.max(this.sucursalNames.length - MAX_CHIPS, 0);
  }

  toggleGroups(): void {
    this.showAllGroups = !this.showAllGroups;
  }

  toggleSucursales(): void {
    this.showAllSucursales = !this.showAllSucursales;
  }

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
