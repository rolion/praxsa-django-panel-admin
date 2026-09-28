import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ImageUploadComponent } from '../../shared/image-upload/image-upload.component';
import { AlmacenService } from '../almacen.service';

@Component({
  selector: 'app-lamina-edit',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, ImageUploadComponent],
  templateUrl: './lamina-edit.component.html',
})
export class LaminaEditComponent implements OnInit {
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private almacenService = inject(AlmacenService);

  laminaId!: number;
  form!: FormGroup;
  currentImageUrl: string | null = null;
  loading = true;
  saving = false;
  submitted = false;
  errorMessage = '';

  ngOnInit(): void {
    this.laminaId = Number(this.route.snapshot.paramMap.get('id'));
    this.form = this.fb.group({
      name: ['', Validators.required],
      description: ['', Validators.required],
      image: [undefined],
    });

    this.almacenService.getLamina(this.laminaId).subscribe({
      next: (lamina) => {
        this.currentImageUrl = lamina.image;
        this.form.patchValue({ name: lamina.name, description: lamina.description });
        this.loading = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar la lamina.';
        this.loading = false;
      },
    });
  }

  save(): void {
    this.submitted = true;
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving = true;
    this.errorMessage = '';
    const { name, description } = this.form.value;
    const imageControl = this.form.get('image')!;
    // Solo se manda la imagen si el usuario la toco -- ver comentario de
    // ImageUploadComponent (mismo criterio que model-edit.component.ts de
    // Vehiculos).
    const image = imageControl.dirty ? imageControl.value : undefined;
    this.almacenService.updateLamina(this.laminaId, name, description, image).subscribe({
      next: () => this.router.navigate(['/almacen/laminas/view', this.laminaId]),
      error: (err) => {
        this.saving = false;
        this.errorMessage =
          err?.error?.name?.[0] || err?.error?.description?.[0] || err?.error?.image?.[0] ||
          'No se pudo guardar la lamina.';
      },
    });
  }
}
