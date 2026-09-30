import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { AuthService } from '@core';
import { AccesoMode } from './cliente.model';
import { ClienteService } from './cliente.service';

/** Campos que el servidor valida en la etapa 1 del registro: un error en alguno vuelve a ella. */
const STEP1_FIELDS = ['name', 'lastname', 'email', 'phone_number', 'car_plate'];

/** Las dos contraseñas deben coincidir (solo se valida en el cliente; el servidor recibe una). */
export function passwordsMatch(group: AbstractControl): ValidationErrors | null {
  const password = group.get('password')?.value;
  const confirm = group.get('confirm')?.value;
  return password && confirm && password !== confirm ? { mismatch: true } : null;
}

/** Modal de acceso: iniciar sesion o crear cuenta (registro en 2 etapas). No cambia de
 * ruta: la cotizacion queda intacta detras (DDR-pricing-calculator-screen-flujo-cliente).
 * Se cierra con `true` cuando la persona queda con sesion iniciada.
 *
 * API real: POST product/api-panel-admin-token-auth/ (login, via `AuthService`) y
 * POST product/client/register (alta). */
@Component({
  selector: 'app-acceso-modal',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './acceso-modal.component.html',
})
export class AccesoModalComponent {
  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  private clienteService = inject(ClienteService);
  activeModal = inject(NgbActiveModal);

  /** Los fija quien abre el modal (`componentInstance`). */
  message = '';

  mode = signal<AccesoMode>('login');
  step = signal<1 | 2>(1);
  busy = signal(false);
  errorMessage = signal('');
  showPassword = signal(false);
  /** Errores del servidor por campo (se limpian al editar). */
  serverErrors = signal<Record<string, string>>({});
  submittedStep1 = false;
  submittedStep2 = false;
  submittedLogin = false;

  loginForm: FormGroup = this.fb.group({
    username: ['', Validators.required],
    password: ['', Validators.required],
  });

  step1: FormGroup = this.fb.group({
    name: ['', [Validators.required, Validators.maxLength(150)]],
    lastname: ['', [Validators.required, Validators.maxLength(150)]],
    email: ['', [Validators.required, Validators.email, Validators.maxLength(100)]],
    phone_number: ['', [Validators.required, Validators.pattern(/^\+?\d{7,11}$/)]],
    car_plate: ['', [Validators.required, Validators.maxLength(10)]],
  });

  step2: FormGroup = this.fb.group(
    {
      username: ['', [Validators.required, Validators.maxLength(150), Validators.pattern(/^\S+$/)]],
      password: ['', [Validators.required, Validators.minLength(8)]],
      confirm: ['', Validators.required],
    },
    { validators: passwordsMatch }
  );

  setMode(mode: AccesoMode): void {
    this.mode.set(mode);
    this.errorMessage.set('');
    this.serverErrors.set({});
  }

  togglePassword(): void {
    this.showPassword.update((value) => !value);
  }

  // ---- iniciar sesion ----

  login(): void {
    this.submittedLogin = true;
    this.errorMessage.set('');
    if (this.loginForm.invalid) {
      return;
    }
    this.busy.set(true);
    const { username, password } = this.loginForm.getRawValue();
    this.authService.login(username, password).subscribe({
      next: () => this.activeModal.close(true),
      error: (error: HttpErrorResponse) => {
        this.busy.set(false);
        this.errorMessage.set(
          error.status === 0 ? 'No se pudo conectar, inténtalo de nuevo más tarde' : 'Credenciales inválidas'
        );
      },
    });
  }

  // ---- registro en 2 etapas ----

  nextStep(): void {
    this.submittedStep1 = true;
    this.errorMessage.set('');
    if (this.step1.invalid) {
      this.step1.markAllAsTouched();
      return;
    }
    const usernameControl = this.step2.get('username');
    // Sugerencia: el correo, mientras la persona no haya escrito su propio usuario.
    if (usernameControl && !usernameControl.dirty) {
      usernameControl.setValue(String(this.step1.get('email')?.value ?? '').trim());
    }
    this.step.set(2);
  }

  previousStep(): void {
    this.errorMessage.set('');
    this.step.set(1);
  }

  register(): void {
    this.submittedStep2 = true;
    this.errorMessage.set('');
    this.serverErrors.set({});
    if (this.step2.invalid) {
      this.step2.markAllAsTouched();
      return;
    }
    const profile = this.step1.getRawValue();
    const access = this.step2.getRawValue();
    const username = String(access.username).trim();
    this.busy.set(true);
    this.clienteService
      .register({
        name: profile.name.trim(),
        lastname: profile.lastname.trim(),
        email: profile.email.trim(),
        phone_number: profile.phone_number.trim(),
        car_plate: profile.car_plate.trim(),
        username,
        password: access.password,
      })
      .subscribe({
        next: () => this.loginAfterRegister(username, access.password),
        error: (error: HttpErrorResponse) => {
          this.busy.set(false);
          this.applyServerErrors(error);
        },
      });
  }

  /** La cuenta se crea sin token: se inicia sesion con el login existente y se continua. */
  private loginAfterRegister(username: string, password: string): void {
    this.authService.login(username, password).subscribe({
      next: () => this.activeModal.close(true),
      error: () => {
        this.busy.set(false);
        this.setMode('login');
        this.loginForm.patchValue({ username, password: '' });
        this.errorMessage.set('Tu cuenta fue creada. Inicia sesión para continuar.');
      },
    });
  }

  private applyServerErrors(error: HttpErrorResponse): void {
    const body = error.error as Record<string, unknown> | null;
    if (error.status === 429) {
      this.errorMessage.set('Demasiados intentos. Inténtalo de nuevo más tarde.');
      return;
    }
    if (error.status === 0 || !body || typeof body !== 'object') {
      this.errorMessage.set('No se pudo crear la cuenta, inténtalo de nuevo más tarde');
      return;
    }
    const errors: Record<string, string> = {};
    for (const [field, value] of Object.entries(body)) {
      errors[field] = Array.isArray(value) ? value.join(' ') : String(value);
    }
    this.serverErrors.set(errors);
    if (Object.keys(errors).some((field) => STEP1_FIELDS.includes(field))) {
      this.step.set(1);
    } else if (!errors['username'] && !errors['password']) {
      this.errorMessage.set(Object.values(errors).join(' '));
    }
  }

  clearServerError(field: string): void {
    if (this.serverErrors()[field]) {
      const rest = { ...this.serverErrors() };
      delete rest[field];
      this.serverErrors.set(rest);
    }
  }

  // ---- helpers de plantilla ----

  invalid(group: FormGroup, field: string, submitted: boolean): boolean {
    const control = group.get(field);
    return !!control && control.invalid && (control.touched || submitted);
  }

  close(): void {
    if (!this.busy()) {
      this.activeModal.dismiss();
    }
  }
}
