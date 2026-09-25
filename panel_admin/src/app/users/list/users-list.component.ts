import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { FeatherModule } from 'angular-feather';
import Swal from 'sweetalert2';
import { AppUser } from '../users.model';
import { UsersService } from '../users.service';

@Component({
  selector: 'app-users-list',
  standalone: true,
  imports: [FormsModule, RouterLink, NgxDatatableModule, FeatherModule],
  templateUrl: './users-list.component.html',
})
export class UsersListComponent implements OnInit {
  private usersService = inject(UsersService);

  rows: AppUser[] = [];
  includeInactive = false;
  loadingIndicator = true;
  errorMessage = '';

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loadingIndicator = true;
    this.usersService.listUsers(this.includeInactive).subscribe({
      next: (users) => {
        this.rows = users;
        this.loadingIndicator = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar el listado de usuarios.';
        this.loadingIndicator = false;
      },
    });
  }

  onToggleIncludeInactive(): void {
    this.load();
  }

  deactivate(user: AppUser): void {
    Swal.fire({
      title: `¿Eliminar a ${user.username}?`,
      text: 'El usuario quedará inactivo (no se borra físicamente).',
      showCancelButton: true,
      confirmButtonText: 'Eliminar',
      cancelButtonText: 'Cancelar',
    }).then((result) => {
      if (result.isConfirmed) {
        this.usersService.toggleActive(user.id, false).subscribe(() => this.load());
      }
    });
  }

  activate(user: AppUser): void {
    this.usersService.toggleActive(user.id, true).subscribe(() => this.load());
  }
}
