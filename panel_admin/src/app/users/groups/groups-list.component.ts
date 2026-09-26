import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgSelectModule } from '@ng-select/ng-select';
import { forkJoin } from 'rxjs';
import Swal from 'sweetalert2';
import { AppGroup, AppPermission } from '../users.model';
import { UsersService } from '../users.service';

@Component({
  selector: 'app-groups-list',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, NgSelectModule],
  templateUrl: './groups-list.component.html',
})
export class GroupsListComponent implements OnInit {
  private fb = inject(FormBuilder);
  private usersService = inject(UsersService);

  groups: AppGroup[] = [];
  permissions: AppPermission[] = [];
  editingId: number | null = null;
  form!: FormGroup;
  errorMessage = '';

  ngOnInit(): void {
    this.form = this.fb.group({
      name: ['', Validators.required],
      permissions: [[]],
    });
    this.load();
  }

  load(): void {
    forkJoin({
      groups: this.usersService.listGroups(),
      permissions: this.usersService.listPermissions(),
    }).subscribe(({ groups, permissions }) => {
      this.groups = groups;
      this.permissions = permissions;
    });
  }

  permissionNames(group: AppGroup): string {
    return this.permissions
      .filter((permission) => group.permissions.includes(permission.id))
      .map((permission) => permission.name)
      .join(', ');
  }

  startCreate(): void {
    this.editingId = 0;
    this.form.reset({ name: '', permissions: [] });
  }

  startEdit(group: AppGroup): void {
    this.editingId = group.id;
    this.form.setValue({ name: group.name, permissions: group.permissions });
  }

  cancel(): void {
    this.editingId = null;
  }

  save(): void {
    if (this.form.invalid) {
      return;
    }
    this.errorMessage = '';
    const request =
      this.editingId && this.editingId > 0
        ? this.usersService.updateGroup(this.editingId, this.form.value)
        : this.usersService.createGroup(this.form.value);

    request.subscribe({
      next: () => {
        this.editingId = null;
        this.load();
      },
      error: () => {
        this.errorMessage = 'No se pudo guardar el grupo.';
      },
    });
  }

  remove(group: AppGroup): void {
    Swal.fire({
      title: `¿Eliminar el grupo "${group.name}"?`,
      showCancelButton: true,
      confirmButtonText: 'Eliminar',
      cancelButtonText: 'Cancelar',
    }).then((result) => {
      if (result.isConfirmed) {
        this.usersService.deleteGroup(group.id).subscribe(() => this.load());
      }
    });
  }
}
