import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { ImageUploadComponent } from '../../shared/image-upload/image-upload.component';
import { AppCarBrand } from '../vehicles.model';
import { VehiclesService } from '../vehicles.service';

@Component({
  selector: 'app-model-edit',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, ImageUploadComponent],
  templateUrl: './model-edit.component.html',
})
export class ModelEditComponent implements OnInit {
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private vehiclesService = inject(VehiclesService);

  modelId!: number;
  form!: FormGroup;
  brands: AppCarBrand[] = [];
  currentImageUrl: string | null = null;
  loading = true;
  saving = false;
  errorMessage = '';

  ngOnInit(): void {
    this.modelId = Number(this.route.snapshot.paramMap.get('id'));
    this.form = this.fb.group({
      name: ['', Validators.required],
      car_brand_id: [null, Validators.required],
      image: [undefined],
    });

    forkJoin({
      model: this.vehiclesService.getModel(this.modelId),
      brands: this.vehiclesService.listBrands(),
    }).subscribe({
      next: ({ model, brands }) => {
        this.brands = brands;
        this.currentImageUrl = model.image;
        this.form.patchValue({
          name: model.name,
          car_brand_id: model.car_brand_id,
        });
        this.loading = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar el modelo.';
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
    const { name, car_brand_id, image } = this.form.value;
    this.vehiclesService.updateModel(this.modelId, name, car_brand_id, image).subscribe({
      next: () => this.router.navigate(['/vehicles/models/view', this.modelId]),
      error: (err) => {
        this.saving = false;
        this.errorMessage =
          err?.error?.name?.[0] || err?.error?.car_brand_id?.[0] || err?.error?.image?.[0] ||
          'No se pudo guardar el modelo.';
      },
    });
  }
}
