import { Component, DestroyRef, OnInit, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormArray, FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { forkJoin } from 'rxjs';
import { environment } from '../../environments/environment';
import { AuthService } from '@core';
import { SALES_TYPE_INSTALACION, OrdenSucursal, ReelCatalogItem } from '../ordenes/ordenes.model';
import { previewSubtotal, round2 } from '../ordenes/ordenes.calc';
import { AppCarBrand, AppCarModel, AppCarModelPart } from '../vehicles/vehicles.model';
import {
  CalculadoraState,
  CotizacionDraft,
  EmptyReason,
  FilmOption,
  LineFormValue,
  QuoteLine,
  QuoteSummary,
} from './calculadora.model';
import {
  buildWhatsappMessage,
  buildWhatsappUrl,
  draftToState,
  filmOptionsFor,
  formatBs,
} from './calculadora.helpers';
import { CalculadoraService } from './calculadora.service';

/** Calculadora de precios (staff): cotiza antes de crear la proforma.
 * Sucursal/Marca/Modelo -> items del modelo + bobinas de la sucursal -> lamina por
 * item -> total. Los importes son VISTA PREVIA (el servidor recalcula al crear la
 * proforma: ADR-pricing-calculator-screen-cotizacion-en-cliente).
 *
 * API real que se consume (todas ya existen, ver `CalculadoraService`):
 *  - GET product/ordenes/catalogo/sucursales
 *  - GET product/vehicles/brands ; GET product/vehicles/models?car_brand_id=
 *  - GET product/vehicles/models/<id>/items/
 *  - GET product/ordenes/catalogo/bobinas?sucursal= (precio por metro y stock) */
@Component({
  selector: 'app-calculadora',
  templateUrl: './calculadora.component.html',
  imports: [ReactiveFormsModule],
})
export class CalculadoraComponent implements OnInit {
  private fb = inject(FormBuilder);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private service = inject(CalculadoraService);
  private authService = inject(AuthService);

  readonly formatBs = formatBs;
  readonly stepLabels = ['Vehículo', 'Láminas', 'Proforma'];

  // ---- catalogos y estado ----
  sucursales = signal<OrdenSucursal[]>([]);
  brands = signal<AppCarBrand[]>([]);
  models = signal<AppCarModel[]>([]);
  items = signal<AppCarModelPart[]>([]);
  reels = signal<ReelCatalogItem[]>([]);
  state = signal<CalculadoraState>('initial');
  emptyReason = signal<EmptyReason>('sin-items');
  errorMessage = signal('');
  /** Evita mostrar "sin sucursal" antes de que lleguen los catalogos. */
  catalogsLoaded = signal(false);
  /** Se marca al pulsar "Crear Proforma" (paso 3 del stepper). */
  creating = signal(false);
  /** Valor de las filas del FormArray, como signal para que `quote` se recalcule solo. */
  private linesValue = signal<LineFormValue[]>([]);
  private selectedModelId = signal<number | null>(null);
  private selectedSucursalId = signal<number | null>(null);

  // ---- formularios ----
  filters: FormGroup = this.fb.group({
    sucursal: [null as number | null],
    brand: [null as number | null],
    model: [{ value: null as number | null, disabled: true }],
  });
  lines: FormArray<FormGroup> = this.fb.array<FormGroup>([]);

  // ---- derivados ----
  get canCreate(): boolean {
    return this.authService.hasPermission('add_proforma_header');
  }

  selectedModel = computed(() => this.models().find((m) => m.id === this.selectedModelId()) ?? null);
  selectedSucursal = computed(() => this.sucursales().find((s) => s.id === this.selectedSucursalId()) ?? null);

  /** Laminas elegibles por item (mismo orden que `items`). */
  optionsByItem = computed<FilmOption[][]>(() => this.items().map((item) => filmOptionsFor(this.reels(), item)));

  quote = computed<QuoteSummary>(() => {
    const values = this.linesValue();
    const options = this.optionsByItem();
    const lines: QuoteLine[] = this.items().map((item, index) => {
      const value = values[index];
      const film = options[index]?.find((o) => o.key === value?.reel) ?? null;
      const excluded = !!value?.excluded;
      const subtotal =
        film && !excluded
          ? previewSubtotal(
              SALES_TYPE_INSTALACION,
              Number(item.length),
              Number(item.quantity),
              Number(film.unitPrice),
              Number(item.installation_price)
            )
          : 0;
      return { item, film, excluded, subtotal };
    });
    const priced = lines.filter((l) => l.film && !l.excluded);
    return {
      lines,
      total: round2(priced.reduce((sum, l) => sum + l.subtotal, 0)),
      pricedCount: priced.length,
    };
  });

  /** Paso activo del stepper: 1 sin modelo, 2 con modelo, 3 al crear la proforma. */
  step = computed(() => (this.creating() ? 3 : this.selectedModelId() ? 2 : 1));

  ngOnInit(): void {
    this.lines.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.syncLines());
    this.loadCatalogs();
  }

  // ---- carga de catalogos ----

  loadCatalogs(): void {
    this.errorMessage.set('');
    forkJoin({ sucursales: this.service.sucursales(), brands: this.service.brands() }).subscribe({
      next: ({ sucursales, brands }) => {
        this.sucursales.set(sucursales);
        this.brands.set(brands);
        if (sucursales.length === 1) {
          // Con una sola sucursal se fija y se muestra como solo lectura.
          this.filters.get('sucursal')?.setValue(sucursales[0].id);
          this.filters.get('sucursal')?.disable();
          this.selectedSucursalId.set(sucursales[0].id);
        }
        this.catalogsLoaded.set(true);
        this.state.set('initial');
      },
      error: () => this.fail('No se pudieron cargar sucursales y marcas.'),
    });
  }

  onSucursalChange(): void {
    this.selectedSucursalId.set(this.filters.getRawValue().sucursal);
    this.loadQuoteData();
  }

  onBrandChange(): void {
    const brandId = this.filters.getRawValue().brand as number | null;
    this.filters.get('model')?.setValue(null);
    this.selectedModelId.set(null);
    this.models.set([]);
    this.filters.get('model')?.disable();
    this.resetItems();
    this.state.set('initial');
    if (brandId) {
      this.service.modelsByBrand(Number(brandId)).subscribe({
        next: (models) => {
          this.models.set(models);
          this.filters.get('model')?.enable();
        },
        error: () => this.fail('No se pudieron cargar los modelos.'),
      });
    }
  }

  onModelChange(): void {
    const modelId = this.filters.getRawValue().model as number | null;
    this.selectedModelId.set(modelId ? Number(modelId) : null);
    this.loadQuoteData();
  }

  /** Con sucursal y modelo elegidos trae los items del modelo y las bobinas de la sucursal. */
  private loadQuoteData(): void {
    const sucursalId = this.selectedSucursalId();
    const modelId = this.selectedModelId();
    this.resetItems();
    if (!sucursalId || !modelId) {
      this.state.set('initial');
      return;
    }
    this.state.set('loading');
    forkJoin({ items: this.service.items(modelId), reels: this.service.reels(sucursalId) }).subscribe({
      next: ({ items, reels }) => {
        this.items.set(items);
        this.reels.set(reels);
        this.buildLines(items.length);
        if (items.length === 0) {
          this.emptyReason.set('sin-items');
          this.state.set('empty');
        } else if (reels.length === 0) {
          this.emptyReason.set('sin-stock');
          this.state.set('empty');
        } else {
          this.state.set('active');
        }
      },
      error: () => this.fail('No se pudo cargar la información para cotizar.'),
    });
  }

  private fail(message: string): void {
    this.errorMessage.set(message);
    this.state.set('error');
  }

  retry(): void {
    if (this.sucursales().length === 0 && this.brands().length === 0) {
      this.loadCatalogs();
    } else {
      this.loadQuoteData();
    }
  }

  private resetItems(): void {
    this.items.set([]);
    this.reels.set([]);
    this.creating.set(false);
    this.lines.clear({ emitEvent: false });
    this.syncLines();
  }

  private buildLines(count: number): void {
    this.lines.clear({ emitEvent: false });
    for (let i = 0; i < count; i++) {
      this.lines.push(this.fb.group({ reel: [null as string | null], excluded: [false] }), { emitEvent: false });
    }
    this.syncLines();
  }

  private syncLines(): void {
    this.linesValue.set(this.lines.getRawValue() as LineFormValue[]);
  }

  // ---- filas ----

  line(index: number): FormGroup {
    return this.lines.at(index);
  }

  isExcluded(index: number): boolean {
    return !!this.linesValue()[index]?.excluded;
  }

  /** "Quitar" excluye el item del total (no borra la fila): se puede restaurar. */
  toggleExcluded(index: number): void {
    const group = this.line(index);
    const excluded = !group.get('excluded')?.value;
    // La lamina se bloquea mientras el item esta excluido.
    if (excluded) {
      group.get('reel')?.disable({ emitEvent: false });
    } else {
      group.get('reel')?.enable({ emitEvent: false });
    }
    group.get('excluded')?.setValue(excluded);
  }

  /** Aviso rojo cuando ninguna bobina sirve para el item (ancho o metros). */
  noOptionsWarning(index: number): string | null {
    const item = this.items()[index];
    if (item && this.optionsByItem()[index]?.length === 0) {
      return `No hay lámina con stock y ancho suficiente (mínimo ${item.width} m).`;
    }
    return null;
  }

  /** Texto del subtitulo: medidas reales del item. */
  subtitle(item: AppCarModelPart): string {
    return `${item.width} × ${item.length} m · Cantidad ${item.quantity}`;
  }

  /** Icono decorativo segun el nombre del item (no es un dato del backend). */
  iconFor(name: string): string {
    const n = name.toLowerCase();
    if (n.includes('parabrisas') || n.includes('luneta') || n.includes('trasero')) {
      return 'fa-car-side';
    }
    if (n.includes('puerta')) {
      return 'fa-door-closed';
    }
    return 'fa-window-maximize';
  }

  // ---- acciones ----

  get canAct(): boolean {
    return this.quote().pricedCount > 0;
  }

  private vehicleLabel(): string {
    const model = this.selectedModel();
    return model ? `${model.car_brand_name} ${model.name}` : '';
  }

  /** Enlace `wa.me` con el mensaje prearmado. El numero es global
   * (`environment.whatsappNumber`); por sucursal requeriria un campo nuevo en el
   * backend (pendiente de negocio). */
  get whatsappUrl(): string {
    const quote = this.quote();
    const message = buildWhatsappMessage(
      this.vehicleLabel(),
      this.selectedSucursal()?.name ?? '',
      quote.lines
        .filter((l) => l.film && !l.excluded)
        .map((l) => ({ itemName: l.item.car_part_name, filmName: l.film?.name ?? '', subtotal: l.subtotal })),
      quote.total
    );
    return buildWhatsappUrl(environment.whatsappNumber, message);
  }

  openWhatsapp(): void {
    if (this.canAct) {
      window.open(this.whatsappUrl, '_blank', 'noopener');
    }
  }

  /** Borrador que recibe el formulario de proforma (sin datos del cliente). */
  buildDraft(): CotizacionDraft | null {
    const sucursal = this.selectedSucursalId();
    const carModelId = this.selectedModelId();
    if (!sucursal || !carModelId) {
      return null;
    }
    const lines = this.quote()
      .lines.filter((l) => l.film && !l.excluded)
      .map((l) => ({
        carPartId: l.item.car_part_id,
        windowFilm: (l.film as FilmOption).windowFilm,
        width: (l.film as FilmOption).width,
        length: l.item.length,
        quantity: l.item.quantity,
      }));
    return lines.length ? { version: 1, sucursal, carModelId, lines } : null;
  }

  /** Paso 3: abre el formulario de alta con la cotizacion precargada. La barrera
   * real del permiso es el POST de proformas; aqui solo se oculta el boton. */
  createProforma(): void {
    const draft = this.buildDraft();
    if (!draft || !this.canCreate) {
      return;
    }
    this.creating.set(true);
    this.router.navigate(['/ordenes/proformas/create'], { state: draftToState(draft) });
  }
}
