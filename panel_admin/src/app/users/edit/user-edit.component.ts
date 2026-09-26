import { Component, OnInit, inject } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgSelectModule } from '@ng-select/ng-select';
import { forkJoin } from 'rxjs';
import Swal from 'sweetalert2';
import { AppGroup, AppSucursal } from '../users.model';
import { UsersService } from '../users.service';

@Component({
  selector: 'app-user-edit',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, NgSelectModule],
  templateUrl: './user-edit.component.html',
})
export class UserEditComponent implements OnInit {
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private usersService = inject(UsersService);

  userId!: number;
  form!: FormGroup;
  passwordForm!: FormGroup;
  groups: AppGroup[] = [];
  sucursales: AppSucursal[] = [];
  loading = true;
  saving = false;
  errorMessage = '';
  passwordErrorMessage = '';

  ngOnInit(): void {
    this.userId = Number(this.route.snapshot.paramMap.get('id'));

    this.form = this.fb.group({
      first_name: [''],
      last_name: [''],
      email: ['', Validators.email],
      phone_number: [''],
      groups: [[]],
      sucursales: [[]],
    });
    this.passwordForm = this.fb.group({
      password: ['', Validators.required],
      password_confirm: ['', Validators.required],
    });

    forkJoin({
      user: this.usersService.getUser(this.userId),
      groups: this.usersService.listGroups(),
      sucursales: this.usersService.listSucursales(),
    }).subscribe({
      next: ({ user, groups, sucursales }) => {
        this.groups = groups;
        this.sucursales = sucursales;
        this.form.patchValue({
          first_name: user.first_name,
          last_name: user.last_name,
          email: user.email,
          phone_number: user.phone_number,
          groups: user.groups,
          sucursales: user.sucursales,
        });
        this.loading = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar el usuario.';
        this.loading = false;
      },
    });
  }

  save(): void {
    if (this.form.invalid) {
      return;
    }
    this.saving = true;
    this.errorMessage = '';
    this.usersService.updateUser(this.userId, this.form.value).subscribe({
      next: () => this.router.navigate(['/users/view', this.userId]),
      error: () => {
        this.errorMessage = 'No se pudo guardar el usuario.';
        this.saving = false;
      },
    });
  }

  changePassword(): void {
    if (this.passwordForm.invalid) {
      return;
    }
    this.passwordErrorMessage = '';
    const { password, password_confirm } = this.passwordForm.value;
    this.usersService.setPassword(this.userId, password, password_confirm).subscribe({
      next: () => {
        this.passwordForm.reset();
        Swal.fire('Listo', 'La contraseña se actualizó correctamente.', 'success');
      },
      error: (err) => {
        const detail = err?.error?.password?.[0] || err?.error?.password_confirm?.[0];
        this.passwordErrorMessage = detail || 'No se pudo cambiar la contraseña.';
      },
    });
  }
}
