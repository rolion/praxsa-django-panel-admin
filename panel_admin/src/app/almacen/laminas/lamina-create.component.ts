import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ImageUploadComponent } from '../../shared/image-upload/image-upload.component';
import { AlmacenService } from '../almacen.service';

@Component({
  selector: 'app-lamina-create',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, ImageUploadComponent],
  templateUrl: './lamina-create.component.html',
})
export class LaminaCreateComponent implements OnInit {
  private fb = inject(FormBuilder);
  private router = inject(Router);
  private almacenService = inject(AlmacenService);

  form!: FormGroup;
  saving = false;
  errorMessage = '';

  ngOnInit(): void {
    this.form = this.fb.group({
      name: ['', Validators.required],
      description: ['', Validators.required],
      image: [null],
    });
  }

  save(): void {
    if (this.form.invalid) {
      return;
    }
    this.saving = true;
    this.errorMessage = '';
    const { name, description, image } = this.form.value;
    this.almacenService.createLamina(name, description, image).subscribe({
      next: (lamina) => this.router.navigate(['/almacen/laminas/view', lamina.id]),
      error: (err) => {
        this.saving = false;
        this.errorMessage =
          err?.error?.name?.[0] || err?.error?.description?.[0] || err?.error?.image?.[0] ||
          'No se pudo crear la lamina.';
      },
    });
  }
}
