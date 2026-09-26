import { Component, OnInit, inject } from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn,
  Validators,
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { NgSelectModule } from '@ng-select/ng-select';
import { forkJoin } from 'rxjs';
import { AppGroup, AppSucursal } from '../users.model';
import { UsersService } from '../users.service';

function passwordsMatchValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const password = control.get('password')?.value;
    const confirm = control.get('password_confirm')?.value;
    if (password && confirm && password !== confirm) {
      return { passwordMismatch: true };
    }
    return null;
  };
}

@Component({
  selector: 'app-user-create',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, NgSelectModule],
  templateUrl: './user-create.component.html',
})
export class UserCreateComponent implements OnInit {
  private fb = inject(FormBuilder);
  private router = inject(Router);
  private usersService = inject(UsersService);

  step = 1;
  groups: AppGroup[] = [];
  sucursales: AppSucursal[] = [];
  errorMessage = '';
  saving = false;

  credentialsForm!: FormGroup;
  profileForm!: FormGroup;
  groupsForm!: FormGroup;

  ngOnInit(): void {
    this.credentialsForm = this.fb.group(
      {
        username: ['', Validators.required],
        password: ['', Validators.required],
        password_confirm: ['', Validators.required],
        is_active: [true],
      },
      { validators: passwordsMatchValidator() }
    );
    this.profileForm = this.fb.group({
      first_name: [''],
      last_name: [''],
      email: ['', Validators.email],
      phone_number: [''],
      sucursales: [[]],
    });
    this.groupsForm = this.fb.group({
      groups: [[]],
    });

    forkJoin({
      groups: this.usersService.listGroups(),
      sucursales: this.usersService.listSucursales(),
    }).subscribe(({ groups, sucursales }) => {
      this.groups = groups;
      this.sucursales = sucursales;
    });
  }

  // Arrow functions (no `function`) para conservar el `this` cuando el
  // template las pasa como callback a Array.prototype.map.
  groupName = (id: number): string => {
    return this.groups.find((group) => group.id === id)?.name || '';
  };

  sucursalName = (id: number): string => {
    return this.sucursales.find((sucursal) => sucursal.id === id)?.name || '';
  };

  goToStep(step: number): void {
    if (step === 2 && this.credentialsForm.invalid) {
      this.credentialsForm.markAllAsTouched();
      return;
    }
    if (step === 3 && this.profileForm.invalid) {
      this.profileForm.markAllAsTouched();
      return;
    }
    this.step = step;
  }

  confirm(): void {
    this.saving = true;
    this.errorMessage = '';
    const payload = {
      ...this.credentialsForm.value,
      ...this.profileForm.value,
      ...this.groupsForm.value,
    };
    this.usersService.createUser(payload).subscribe({
      next: (user) => this.router.navigate(['/users/view', user.id]),
      error: (err) => {
        this.saving = false;
        const firstFieldError = Object.values(err?.error || {})[0];
        this.errorMessage = Array.isArray(firstFieldError)
          ? (firstFieldError[0] as string)
          : 'No se pudo crear el usuario.';
      },
    });
  }
}
