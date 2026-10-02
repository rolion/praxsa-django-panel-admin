import { Component, OnInit, inject } from '@angular/core';
import {
  AbstractControl,
  FormArray,
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CotizacionDraft } from '../../calculadora/calculadora.model';
import { parseDraft } from '../../calculadora/calculadora.helpers';
import { AppCarModel, AppCarModelPart } from '../../vehicles/vehicles.model';
import { VehiclesService } from '../../vehicles/vehicles.service';
import { previewSubtotal, round2 } from '../ordenes.calc';
import { extractApiError } from '../ordenes.errors';
import {
  AppProformaDetail,
  OrdenSucursal,
  ProformaLinePayload,
  ProformaPayload,
  ReelCatalogItem,
  SALES_TYPE_INSTALACION,
  SALES_TYPE_METRO_LINEAL,
  SalesType,
} from '../ordenes.model';
import { OrdenesService } from '../ordenes.service';

/** Crear y editar proforma (mismo formulario, ver PLAN: un solo componente para
 * no duplicar la logica de lineas). La linea se identifica por bobina (lamina +
 * ancho con stock en la sucursal). Los importes mostrados son una VISTA PREVIA:
 * el servidor recalcula y devuelve los definitivos
 * (ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo). */
@Component({
  selector: 'app-proforma-form',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './proforma-form.component.html',
})
export class ProformaFormComponent implements OnInit {
  private fb = inject(FormBuilder);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private ordenesService = inject(OrdenesService);
  private vehiclesService = inject(VehiclesService);

  readonly SALES_TYPE_INSTALACION = SALES_TYPE_INSTALACION;
  readonly SALES_TYPE_METRO_LINEAL = SALES_TYPE_METRO_LINEAL;

  form!: FormGroup;
  editId: number | null = null;
  sucursales: OrdenSucursal[] = [];
  /** Edicion de una proforma cuya sucursal esta inactiva: solo lectura. */
  sucursalInactiva = false;
  models: AppCarModel[] = [];
  items: AppCarModelPart[] = [];
  reels: ReelCatalogItem[] = [];
  loading = false;
  saving = false;
  submitted = false;
  errorMessage = '';
  infoMessage = '';
  /** Panel de referencia de medidas del modelo (colapsable). */
  showReference = true;
  copiedItemId: number | null = null;
  /** Cotizacion que trae la Calculadora de precios por `history.state` (solo alta). */
  private draft: CotizacionDraft | null = null;

  get isEdit(): boolean {
    return this.editId !== null;
  }

  get lines(): FormArray {
    return this.form.get('items') as FormArray;
  }

  get salesType(): SalesType {
    return this.form.get('sales_type')?.value as SalesType;
  }

  /** Columnas de la tabla de detalle (instalacion muestra item, cantidad y precio de instalacion). */
  get columnCount(): number {
    return this.isInstalacion ? 9 : 6;
  }

  get isInstalacion(): boolean {
    return this.salesType === SALES_TYPE_INSTALACION;
  }

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    this.editId = idParam ? Number(idParam) : null;

    this.form = this.fb.group({
      sales_type: [SALES_TYPE_INSTALACION, Validators.required],
      sucursal: [null as number | null, Validators.required],
      name: ['', [Validators.required, Validators.maxLength(400)]],
      // Reglas espejo del modelo backend (Proforma_Header): email valido,
      // telefono `(\+)*\d{7,11}`, placa maximo 10 caracteres.
      email: ['', [Validators.required, Validators.email]],
      ci_nit: ['', Validators.required],
      phone_number: ['', [Validators.required, Validators.pattern(/(\+)*\d{7,11}/)]],
      car_plate: ['', Validators.maxLength(10)],
      car_model_id: [null as number | null],
      discount: ['0'],
      discount_reason: [''],
      items: this.fb.array([]),
    });
    this.applySalesTypeValidators();
    if (!this.isEdit) {
      this.addLine();
      this.form.get('sales_type')?.valueChanges.subscribe(() => this.onSalesTypeChange());
    }

    if (!this.isEdit) {
      this.draft = parseDraft(history.state);
      if (this.draft) {
        this.applyDraft(this.draft);
      }
    }

    this.vehiclesService.listModels().subscribe((models) => (this.models = models));
    this.ordenesService.listSucursales().subscribe({
      next: (sucursales) => this.onSucursalesLoaded(sucursales),
      error: () => (this.errorMessage = 'No se pudieron cargar las sucursales.'),
    });

    if (this.isEdit) {
      this.loadForEdit();
    }
  }

  private onSucursalesLoaded(todas: OrdenSucursal[]): void {
    // En el alta solo se ofrecen las sucursales ACTIVAS (las inactivas son de solo lectura);
    // al editar se conserva la lista completa para mostrar la sucursal de la proforma.
    const sucursales = this.isEdit ? todas : todas.filter((sucursal) => sucursal.activa !== false);
    this.sucursales = sucursales;
    if (todas.length === 0) {
      this.errorMessage = 'Asigne una sucursal al usuario para crear proformas.';
    } else if (sucursales.length === 0) {
      this.errorMessage = 'No tienes sucursales activas para crear proformas.';
    } else if (!this.isEdit && this.draft && sucursales.some((s) => s.id === this.draft?.sucursal)) {
      // Cotizacion de la calculadora: su sucursal (si esta en el alcance) queda elegida.
      this.form.get('sucursal')?.setValue(this.draft.sucursal);
      if (sucursales.length === 1) {
        this.form.get('sucursal')?.disable();
      }
      this.loadCatalog(this.draft.sucursal);
    } else if (!this.isEdit && sucursales.length === 1) {
      // Con una sola sucursal se fija y se muestra como solo lectura.
      this.form.get('sucursal')?.setValue(sucursales[0].id);
      this.form.get('sucursal')?.disable();
      this.loadCatalog(sucursales[0].id);
    }
  }

  /** Precarga modelo, items y lineas de la cotizacion de la calculadora. El cliente
   * y los demas datos los completa la persona; el servidor recalcula los importes. */
  private applyDraft(draft: CotizacionDraft): void {
    this.form.get('car_model_id')?.setValue(draft.carModelId);
    this.lines.clear();
    draft.lines.forEach((line) =>
      this.lines.push(
        this.newLine({
          car_part: line.carPartId,
          reel: this.reelKey(line.windowFilm, line.width),
          length: line.length,
          quantity: line.quantity,
        })
      )
    );
    this.loadItems(draft.carModelId);
  }

  private loadForEdit(): void {
    this.loading = true;
    this.ordenesService.getProforma(this.editId as number).subscribe({
      next: (proforma) => {
        if (proforma.is_close) {
          this.router.navigate(['/ordenes/proformas/view', proforma.id]);
          return;
        }
        this.patchFromProforma(proforma);
        this.loading = false;
      },
      error: () => {
        this.errorMessage = 'No se pudo cargar la proforma.';
        this.loading = false;
      },
    });
  }

  private patchFromProforma(proforma: AppProformaDetail): void {
    if (proforma.sucursal_activa === false) {
      // Sucursal inactiva: la proforma se ve pero no se edita (el servidor responde 409).
      this.sucursalInactiva = true;
      this.errorMessage = 'La sucursal de esta proforma está inactiva: solo lectura, no se pueden guardar cambios.';
    }
    this.form.patchValue({
      sales_type: proforma.sales_type,
      sucursal: proforma.sucursal,
      name: proforma.name,
      email: proforma.email ?? '',
      ci_nit: proforma.ci_nit ?? '',
      phone_number: proforma.phone_number,
      car_plate: proforma.car_plate ?? '',
      car_model_id: proforma.car_model_id,
      discount: proforma.discount,
      discount_reason: proforma.discount_reason ?? '',
    });
    // El tipo de venta y la sucursal no se pueden cambiar al editar.
    this.form.get('sales_type')?.disable();
    this.form.get('sucursal')?.disable();
    this.applySalesTypeValidators();
    this.lines.clear();
    proforma.items.forEach((item) =>
      this.lines.push(
        this.newLine({
          car_part: item.car_part,
          reel: this.reelKey(item.window_film, item.width),
          length: item.length,
          quantity: item.quantity,
        })
      )
    );
    this.applySalesTypeValidators();
    if (proforma.sucursal) {
      this.loadCatalog(proforma.sucursal);
    }
    if (proforma.car_model_id) {
      this.loadItems(proforma.car_model_id);
    }
  }

  // ---- catalogos dependientes ----

  /** Clave de una bobina (lamina + ancho). El ancho se normaliza a 2 decimales para que
   * catalogo y lineas guardadas coincidan aunque lleguen como `1.5` o `"1.50"`
   * (REV-2026-09-30-modulo-ordenes-proforma-nota-trabajo-02). */
  reelKey(windowFilm: number, width: string | number): string {
    return `${windowFilm}|${Number(width).toFixed(2)}`;
  }

  onSucursalChange(): void {
    const sucursalId = this.form.get('sucursal')?.value as number | null;
    this.reels = [];
    if (sucursalId) {
      this.loadCatalog(sucursalId, true);
    }
  }

  private loadCatalog(sucursalId: number, clearSelections = false): void {
    this.ordenesService.listBobinas(sucursalId).subscribe({
      next: (reels) => {
        this.reels = reels;
        const keys = new Set(reels.map((r) => this.reelKey(r.window_film, r.width)));
        let removed = false;
        this.lines.controls.forEach((line) => {
          const key = line.get('reel')?.value as string | null;
          if (key && (clearSelections || !keys.has(key))) {
            line.get('reel')?.setValue(null);
            removed = true;
          }
        });
        this.infoMessage = removed
          ? 'Algunas bobinas ya no están disponibles en la sucursal; vuelva a seleccionarlas.'
          : '';
      },
      error: () => (this.errorMessage = 'No se pudo cargar el catálogo de bobinas.'),
    });
  }

  onModelChange(): void {
    const modelId = this.form.get('car_model_id')?.value as number | null;
    this.items = [];
    this.lines.controls.forEach((line) => line.get('car_part')?.setValue(null));
    if (modelId) {
      this.loadItems(modelId);
    }
  }

  private loadItems(modelId: number): void {
    this.vehiclesService.listModelItems(modelId).subscribe({
      next: (items) => (this.items = items),
      error: () => (this.errorMessage = 'No se pudieron cargar los items del modelo.'),
    });
  }

  private onSalesTypeChange(): void {
    this.applySalesTypeValidators();
    this.lines.clear();
    this.addLine();
    // El modelo (y sus items de referencia) se conserva: en metro lineal es opcional.
  }

  private applySalesTypeValidators(): void {
    const instalacion = this.isInstalacion;
    const model = this.form.get('car_model_id');
    const plate = this.form.get('car_plate');
    model?.setValidators(instalacion ? [Validators.required] : []);
    plate?.setValidators(
      instalacion ? [Validators.required, Validators.maxLength(10)] : [Validators.maxLength(10)]
    );
    model?.updateValueAndValidity({ emitEvent: false });
    plate?.updateValueAndValidity({ emitEvent: false });
    this.lines.controls.forEach((line) => this.applyLineValidators(line));
  }

  // ---- referencia de items del modelo (solo lectura) ----

  get hasReference(): boolean {
    return !!this.form.get('car_model_id')?.value && this.items.length > 0;
  }

  toggleReference(): void {
    this.showReference = !this.showReference;
  }

  /** Copia "ancho x largo" de un item para calcular los metros a vender. */
  copyMeasure(item: AppCarModelPart): void {
    const text = `${item.width} x ${item.length}`;
    navigator.clipboard?.writeText(text).then(
      () => {
        this.copiedItemId = item.id;
        setTimeout(() => (this.copiedItemId = null), 1500);
      },
      () => undefined
    );
  }

  // ---- lineas ----

  private newLine(value?: {
    car_part?: number | null;
    reel?: string | null;
    length?: string;
    quantity?: number;
  }): FormGroup {
    const line = this.fb.group({
      car_part: [value?.car_part ?? null],
      reel: [value?.reel ?? null, Validators.required],
      length: [value?.length ?? '', [Validators.required, Validators.min(0.01)]],
      quantity: [value?.quantity ?? 1],
    });
    this.applyLineValidators(line);
    return line;
  }

  private applyLineValidators(line: AbstractControl): void {
    const part = line.get('car_part');
    const quantity = line.get('quantity');
    part?.setValidators(this.isInstalacion ? [Validators.required] : []);
    quantity?.setValidators(this.isInstalacion ? [Validators.required, Validators.min(1)] : []);
    part?.updateValueAndValidity({ emitEvent: false });
    quantity?.updateValueAndValidity({ emitEvent: false });
  }

  addLine(): void {
    this.lines.push(this.newLine());
  }

  removeLine(index: number): void {
    if (this.lines.length > 1) {
      this.lines.removeAt(index);
    }
  }

  /** Al elegir el item se precargan largo y cantidad del item (Car_Model_Part). */
  onItemChange(index: number): void {
    const line = this.lines.at(index);
    const item = this.itemOf(index);
    if (item) {
      line.patchValue({ length: item.length, quantity: item.quantity });
    }
  }

  reelOf(index: number): ReelCatalogItem | undefined {
    const key = this.lines.at(index).get('reel')?.value as string | null;
    return key ? this.reels.find((r) => this.reelKey(r.window_film, r.width) === key) : undefined;
  }

  itemOf(index: number): AppCarModelPart | undefined {
    const partId = this.lines.at(index).get('car_part')?.value as number | null;
    return partId ? this.items.find((i) => i.car_part_id === partId) : undefined;
  }

  // ---- vista previa de importes (no autoritativa) ----

  private quantityOf(index: number): number {
    return this.isInstalacion ? Number(this.lines.at(index).get('quantity')?.value) : 0;
  }

  lineSubtotal(index: number): number {
    const reel = this.reelOf(index);
    if (!reel) {
      return 0;
    }
    return previewSubtotal(
      this.salesType,
      Number(this.lines.at(index).get('length')?.value),
      this.quantityOf(index),
      Number(reel.unit_price),
      Number(this.itemOf(index)?.installation_price ?? 0)
    );
  }

  get total(): number {
    let sum = 0;
    for (let i = 0; i < this.lines.length; i++) {
      sum += this.lineSubtotal(i);
    }
    return round2(sum);
  }

  get discountValue(): number {
    const value = Number(this.form.get('discount')?.value);
    return Number.isFinite(value) ? value : 0;
  }

  get totalAPagar(): number {
    return round2(this.total - this.discountValue);
  }

  /** Reglas del descuento (espejo de Sale_header.py / del serializer): no
   * negativo, hasta 50 % del total y con motivo si es mayor a 0. */
  get discountError(): string | null {
    if (this.discountValue < 0) {
      return 'El descuento no puede ser negativo.';
    }
    if (this.discountValue > this.total * 0.5) {
      return 'El descuento no puede ser mayor que el 50% del precio total.';
    }
    if (this.discountValue > 0 && !String(this.form.get('discount_reason')?.value || '').trim()) {
      return 'Debe agregar el motivo del descuento o quien lo aprueba.';
    }
    return null;
  }

  widthWarning(index: number): string | null {
    const reel = this.reelOf(index);
    const item = this.itemOf(index);
    if (this.isInstalacion && reel && item && Number(reel.width) < Number(item.width)) {
      return `Ancho insuficiente: mínimo requerido ${item.width} m.`;
    }
    return null;
  }

  stockWarning(index: number): string | null {
    const reel = this.reelOf(index);
    if (!reel) {
      return null;
    }
    const needed = Number(this.lines.at(index).get('length')?.value) * Math.max(this.quantityOf(index), 1);
    if (Number.isFinite(needed) && needed > Number(reel.available_meters)) {
      return `Se necesitan ${needed} m y hay ${reel.available_meters} m disponibles (se valida al generar la nota de trabajo).`;
    }
    return null;
  }

  // ---- guardar ----

  save(): void {
    if (this.sucursalInactiva) {
      return;
    }
    this.submitted = true;
    if (this.form.invalid || this.discountError) {
      this.form.markAllAsTouched();
      return;
    }
    const raw = this.form.getRawValue();
    const instalacion = this.isInstalacion;
    const items: ProformaLinePayload[] = raw.items.map(
      (line: { car_part: number | null; reel: string; length: number | string; quantity: number }) => {
        const [film, width] = line.reel.split('|');
        const payload: ProformaLinePayload = {
          window_film: Number(film),
          width,
          length: String(line.length),
        };
        if (instalacion) {
          payload.car_part = line.car_part;
          payload.quantity = Number(line.quantity);
        }
        return payload;
      }
    );
    const payload: ProformaPayload = {
      name: raw.name,
      email: raw.email,
      ci_nit: raw.ci_nit,
      phone_number: raw.phone_number,
      car_plate: raw.car_plate,
      car_model_id: raw.car_model_id,
      discount: String(raw.discount || '0'),
      discount_reason: raw.discount_reason || '',
      items,
    };

    this.saving = true;
    this.errorMessage = '';
    const request$ = this.isEdit
      ? this.ordenesService.updateProforma(this.editId as number, payload)
      : this.ordenesService.createProforma({
          ...payload,
          sales_type: raw.sales_type,
          sucursal: raw.sucursal,
        });
    request$.subscribe({
      next: (proforma) => this.router.navigate(['/ordenes/proformas/view', proforma.id]),
      error: (err) => {
        this.saving = false;
        this.errorMessage = extractApiError(err, 'No se pudo guardar la proforma.');
      },
    });
  }
}
