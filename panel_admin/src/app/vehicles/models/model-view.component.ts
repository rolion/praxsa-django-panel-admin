import { Component, OnInit, TemplateRef, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import Swal from 'sweetalert2';
import { AppCarModel, AppCarModelPart, AppCarPart } from '../vehicles.model';
import { VehiclesService } from '../vehicles.service';

type AddItemMode = 'existing' | 'new';

/** Detalle de un Modelo: imagen, marca, nombre, y sus items asociados
 * (Car_Model_Part). "Agregar item" permite crear uno nuevo o buscar y
 * asociar uno existente, capturando ancho/largo/cantidad/precio de
 * instalación -- ver ADR-modulo-vehiculos-relacion-modelo-item: son
 * obligatorios porque la calculadora de precios de proformas los usa en
 * vivo, no son un detalle cosmético. */
@Component({
  selector: 'app-model-view',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './model-view.component.html',
})
export class ModelViewComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private vehiclesService = inject(VehiclesService);
  private modalService = inject(NgbModal);
  private fb = inject(FormBuilder);

  modelId!: number;
  model: AppCarModel | null = null;
  items: AppCarModelPart[] = [];
  loading = true;
  errorMessage = '';

  addForm!: FormGroup;
  mode: AddItemMode = 'existing';
  availableParts: AppCarPart[] = [];
  filteredParts: AppCarPart[] = [];
  saving = false;
  addError = '';

  ngOnInit(): void {
    this.modelId = Number(this.route.snapshot.paramMap.get('id'));
    this.addForm = this.fb.group({
      car_part_id: [null],
      new_car_part_name: [''],
      width: ['', Validators.required],
      length: ['', Validators.required],
      quantity: [1, [Validators.required, Validators.min(1)]],
      installation_price: ['', Validators.required],
    });
    this.load();
  }

  load(): void {
    this.loading = true;
    this.vehiclesService.getModel(this.modelId).subscribe({
      next: (model) => {
        this.model = model;
        this.loadItems();
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar el modelo.';
        this.loading = false;
      },
    });
  }

  private loadItems(): void {
    this.vehiclesService.listModelItems(this.modelId).subscribe({
      next: (items) => {
        this.items = items;
        this.loading = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar los items del modelo.';
        this.loading = false;
      },
    });
  }

  openAddItem(content: TemplateRef<unknown>): void {
    this.addError = '';
    this.mode = 'existing';
    this.addForm.reset({ quantity: 1 });
    const associatedIds = this.items.map((item) => item.car_part_id);
    this.vehiclesService.listParts().subscribe((parts) => {
      this.availableParts = parts.filter((part) => !associatedIds.includes(part.id));
      this.filteredParts = this.availableParts;
    });
    this.modalService.open(content, { ariaLabelledBy: 'modal-basic-title', size: 'lg' });
  }

  setMode(mode: AddItemMode): void {
    this.mode = mode;
    this.addForm.patchValue({ car_part_id: null, new_car_part_name: '' });
  }

  filterParts(event: Event): void {
    const val = (event.target as HTMLInputElement).value.toLowerCase();
    this.filteredParts = this.availableParts.filter(
      (part) => !val || part.name.toLowerCase().indexOf(val) !== -1
    );
  }

  selectPart(part: AppCarPart): void {
    this.addForm.patchValue({ car_part_id: part.id });
  }

  saveItem(): void {
    if (this.addForm.invalid) {
      return;
    }
    const { car_part_id, new_car_part_name, width, length, quantity, installation_price } =
      this.addForm.value;
    if (this.mode === 'existing' && !car_part_id) {
      this.addError = 'Seleccione un item de la lista.';
      return;
    }
    if (this.mode === 'new' && !new_car_part_name) {
      this.addError = 'Ingrese el nombre del nuevo item.';
      return;
    }

    this.saving = true;
    this.addError = '';
    const payload =
      this.mode === 'existing'
        ? { car_part_id, width, length, quantity, installation_price }
        : { new_car_part_name, width, length, quantity, installation_price };

    this.vehiclesService.addModelItem(this.modelId, payload).subscribe({
      next: () => {
        this.saving = false;
        this.modalService.dismissAll();
        this.load();
      },
      error: (err) => {
        this.saving = false;
        this.addError =
          err?.error?.non_field_errors?.[0] || err?.error?.detail || 'No se pudo asociar el item.';
      },
    });
  }

  removeItem(item: AppCarModelPart): void {
    Swal.fire({
      title: `¿Quitar ${item.car_part_name} de este modelo?`,
      showCancelButton: true,
      confirmButtonText: 'Quitar',
      cancelButtonText: 'Cancelar',
    }).then((result) => {
      if (result.isConfirmed) {
        this.vehiclesService.removeModelItem(this.modelId, item.id).subscribe(() => this.load());
      }
    });
  }
}
