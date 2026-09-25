import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import Swal from 'sweetalert2';
import { AppSucursal } from '../users.model';
import { UsersService } from '../users.service';

@Component({
  selector: 'app-sucursales-list',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './sucursales-list.component.html',
})
export class SucursalesListComponent implements OnInit {
  private fb = inject(FormBuilder);
  private usersService = inject(UsersService);

  sucursales: AppSucursal[] = [];
  editingId: number | null = null;
  form!: FormGroup;
  errorMessage = '';

  ngOnInit(): void {
    this.form = this.fb.group({
      name: ['', Validators.required],
      address: [''],
      phone_number: [''],
      enable_to_install_windows_film: [true],
    });
    this.load();
  }

  load(): void {
    this.usersService.listSucursales().subscribe((sucursales) => (this.sucursales = sucursales));
  }

  startCreate(): void {
    this.editingId = 0;
    this.form.reset({ name: '', address: '', phone_number: '', enable_to_install_windows_film: true });
  }

  startEdit(sucursal: AppSucursal): void {
    this.editingId = sucursal.id;
    this.form.setValue({
      name: sucursal.name,
      address: sucursal.address,
      phone_number: sucursal.phone_number,
      enable_to_install_windows_film: sucursal.enable_to_install_windows_film,
    });
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
        ? this.usersService.updateSucursal(this.editingId, this.form.value)
        : this.usersService.createSucursal(this.form.value);

    request.subscribe({
      next: () => {
        this.editingId = null;
        this.load();
      },
      error: () => {
        this.errorMessage = 'No se pudo guardar la sucursal.';
      },
    });
  }

  remove(sucursal: AppSucursal): void {
    Swal.fire({
      title: `¿Eliminar la sucursal "${sucursal.name}"?`,
      showCancelButton: true,
      confirmButtonText: 'Eliminar',
      cancelButtonText: 'Cancelar',
    }).then((result) => {
      if (result.isConfirmed) {
        this.usersService.deleteSucursal(sucursal.id).subscribe(() => this.load());
      }
    });
  }
}
