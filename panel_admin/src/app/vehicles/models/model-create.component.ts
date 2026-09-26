import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ImageUploadComponent } from '../../shared/image-upload/image-upload.component';
import { AppCarBrand } from '../vehicles.model';
import { VehiclesService } from '../vehicles.service';

@Component({
  selector: 'app-model-create',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, ImageUploadComponent],
  templateUrl: './model-create.component.html',
})
export class ModelCreateComponent implements OnInit {
  private fb = inject(FormBuilder);
  private router = inject(Router);
  private vehiclesService = inject(VehiclesService);

  form!: FormGroup;
  brands: AppCarBrand[] = [];
  saving = false;
  errorMessage = '';

  ngOnInit(): void {
    this.form = this.fb.group({
      name: ['', Validators.required],
      car_brand_id: [null, Validators.required],
      image: [null],
    });
    this.vehiclesService.listBrands().subscribe((brands) => (this.brands = brands));
  }

  save(): void {
    if (this.form.invalid) {
      return;
    }
    this.saving = true;
    this.errorMessage = '';
    const { name, car_brand_id, image } = this.form.value;
    this.vehiclesService.createModel(name, car_brand_id, image).subscribe({
      next: (model) => this.router.navigate(['/vehicles/models/view', model.id]),
      error: (err) => {
        this.saving = false;
        this.errorMessage =
          err?.error?.name?.[0] || err?.error?.car_brand_id?.[0] || err?.error?.image?.[0] ||
          'No se pudo crear el modelo.';
      },
    });
  }
}
