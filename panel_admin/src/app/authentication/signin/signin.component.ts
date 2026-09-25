import { Component, OnInit, inject } from '@angular/core';
import { Router } from '@angular/router';
import { UntypedFormBuilder, UntypedFormGroup, Validators, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { FeatherModule } from 'angular-feather';
import { AuthService } from '@core';
@Component({
    selector: 'app-signin',
    templateUrl: './signin.component.html',
    styleUrls: ['./signin.component.scss'],
    imports: [
        FormsModule,
        ReactiveFormsModule,
        FeatherModule,
    ]
})
export class SigninComponent implements OnInit {
  private formBuilder = inject(UntypedFormBuilder);
  private router = inject(Router);
  private authService = inject(AuthService);

  loginForm!: UntypedFormGroup;
  submitted = false;
  returnUrl!: string;
  error = '';
  hide = true;
  constructor() { }
  ngOnInit() {
    this.loginForm = this.formBuilder.group({
      username: ['', Validators.required],
      password: ['', Validators.required],
    });
  }
  get f() {
    return this.loginForm.controls;
  }
  onSubmit() {
    this.submitted = true;
    this.error = '';

    if (this.loginForm.invalid) {
      this.error = 'Usuario y contraseña son obligatorios';
      return;
    }

    this.authService
      .login(this.f['username'].value, this.f['password'].value)
      .subscribe({
        next: () => {
          this.router.navigate(['/dashboard/main']);
        },
        error: (error: HttpErrorResponse) => {
          this.error =
            error.status === 0
              ? 'Algo salió mal, inténtalo de nuevo más tarde'
              : 'Credenciales inválidas';
          this.submitted = false;
        },
      });
  }
}
