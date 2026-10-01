import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, OnInit, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormArray, FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { forkJoin, switchMap } from 'rxjs';
import { environment } from '../../environments/environment';
import { AuthService } from '@core';
import { AccesoModalService } from '../cliente/acceso-modal.service';
import { ClientProfile, InvoicePayload } from '../cliente/cliente.model';
import { ClienteService } from '../cliente/cliente.service';
import { extractApiError } from '../ordenes/ordenes.errors';
import { SALES_TYPE_INSTALACION, ReelCatalogItem } from '../ordenes/ordenes.model';
import { previewSubtotal, round2 } from '../ordenes/ordenes.calc';
import { AppCarModelPart } from '../vehicles/vehicles.model';
import {
  CalcBrand,
  CalcModel,
  CalcSucursal,
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

/** Calculadora de precios: cotiza sin sesion y, al guardar, pide login/registro en un modal
 * (DDR-pricing-calculator-screen-flujo-cliente).
 * Sucursal/Marca/Modelo -> items del modelo + bobinas de la sucursal -> lamina por item ->
 * total. Los importes son VISTA PREVIA: el servidor recalcula al guardar la proforma.
 *
 * API real que se consume (ver `CalculadoraService` y `ClienteService`):
 *  - publica:  GET product/calculator_info, product/model_parts/<id>, product/get_inventory/<sucursal>/0/0
 *  - cliente:  GET product/client/me  y  POST product/invoice (guardar la proforma)
 * Staff con permiso `add_proforma_header` conserva el camino de la v1: abre el formulario
 * interno de Ordenes con la cotizacion precargada. */
@Component({
  selector: 'app-calculadora',
  templateUrl: './calculadora.component.html',
  imports: [ReactiveFormsModule],
})
export class CalculadoraComponent implements OnInit {
  private fb = inject(FormBuilder);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);
  private service = inject(CalculadoraService);
  private clienteService = inject(ClienteService);
  private accesoModal = inject(AccesoModalService);
  private toastr = inject(ToastrService);
  authService = inject(AuthService);

  readonly formatBs = formatBs;
  readonly stepLabels = ['Vehículo', 'Láminas', 'Proforma'];

  // ---- catalogos y estado ----
  sucursales = signal<CalcSucursal[]>([]);
  brands = signal<CalcBrand[]>([]);
  private allModels = signal<CalcModel[]>([]);
  models = signal<CalcModel[]>([]);
  items = signal<AppCarModelPart[]>([]);
  reels = signal<ReelCatalogItem[]>([]);
  state = signal<CalculadoraState>('initial');
  emptyReason = signal<EmptyReason>('sin-items');
  errorMessage = signal('');
  /** Evita mostrar "sin sucursal" antes de que lleguen los catalogos. */
  catalogsLoaded = signal(false);
  /** Se marca al pulsar "Crear Proforma" (paso 3 del stepper). */
  creating = signal(false);
  /** Guardando la proforma (deshabilita el boton: evita doble envio). */
  saving = signal(false);
  saveError = signal('');
  /** Perfil del cliente con sesion (solo en memoria, ADR-003). */
  profile = signal<ClientProfile | null>(null);
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
  /** "Crear Proforma" lo ve quien no tiene sesion y el cliente; el staff solo con permiso. La
   * barrera real es el POST (token + permisos), ver ADR-pricing-calculator-screen-sesion-cliente-aislamiento. */
  get showCreate(): boolean {
    return !this.authService.isStaff || this.authService.hasPermission('add_proforma_header');
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
    // El perfil se carga al tener sesion de cliente (inicio o login desde el encabezado/modal).
    this.authService.currentUser.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.refreshProfile());
    // Sesion de cliente vencida (401): reabre el modal y reintenta guardar sin perder la cotizacion.
    this.authService.sessionExpired$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.onSessionExpired());
    this.loadCatalogs();
    // Escucha los parametros (no el snapshot): el componente se reutiliza si ya estamos en
    // /calculadora y el SessionGuard redirige aqui desde /mis-proformas.
    this.route.queryParamMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => this.openAccessFromRoute(!!params.get('acceso')));
  }

  // ---- sesion ----

  private refreshProfile(): void {
    if (!this.authService.isClient) {
      this.profile.set(null);
      return;
    }
    this.clienteService.me().subscribe({
      next: (profile) => this.profile.set(profile),
      error: () => this.profile.set(null),
    });
  }

  /** `?acceso=1` (lo pone `SessionGuard` al entrar a `/mis-proformas` sin sesion). */
  private openAccessFromRoute(requested: boolean): void {
    if (requested && !this.authService.isLoggedIn) {
      this.accesoModal.open('login', 'Inicia sesión o crea tu cuenta para ver tus proformas.').then((ok) => {
        this.router.navigate(ok && this.authService.isClient ? ['/mis-proformas'] : ['/calculadora'], {
          replaceUrl: true,
        });
      });
    }
  }

  // ---- carga de catalogos ----

  loadCatalogs(): void {
    this.errorMessage.set('');
    this.service.catalog().subscribe({
      next: ({ sucursales, brands, models }) => {
        this.sucursales.set(sucursales);
        this.brands.set(brands);
        this.allModels.set(models);
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
    this.resetItems();
    this.state.set('initial');
    const models = brandId ? this.allModels().filter((m) => m.brand_id === Number(brandId)) : [];
    this.models.set(models);
    if (models.length > 0) {
      this.filters.get('model')?.enable();
    } else {
      this.filters.get('model')?.disable();
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
    this.saveError.set('');
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
    return model ? `${model.brand_name} ${model.name}` : '';
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

  /** Borrador de la cotizacion (lo recibe el formulario interno en el camino de staff). */
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

  /** Cuerpo de `POST product/invoice` con los datos de la cuenta. Los importes son los de
   * la vista previa: el servidor los ignora y recalcula (ADR-004). */
  buildInvoice(profile: ClientProfile): InvoicePayload | null {
    const sucursal = this.selectedSucursalId();
    const carModelId = this.selectedModelId();
    const quote = this.quote();
    if (!sucursal || !carModelId || quote.pricedCount === 0) {
      return null;
    }
    return {
      name: `${profile.name} ${profile.lastname}`.trim(),
      email: profile.email,
      car_plate: profile.car_plate,
      car_model_id: carModelId,
      total_price: quote.total.toFixed(2),
      phone_number: profile.phone_number,
      ci_nit: profile.ci_nit ? profile.ci_nit : null,
      sucursal,
      carPartItems: quote.lines
        .filter((l) => l.film && !l.excluded)
        .map((l) => ({
          car_part: l.item.car_part_id,
          width: (l.film as FilmOption).width,
          length: l.item.length,
          quantity: l.item.quantity,
          window_film: (l.film as FilmOption).windowFilm,
          installation_price: l.item.installation_price,
          window_film_price: (l.film as FilmOption).unitPrice,
          sub_total: l.subtotal.toFixed(2),
        })),
    };
  }

  /** "Crear Proforma": staff (con permiso) -> formulario interno; resto -> guardar con la
   * cuenta del cliente, pidiendo login/registro si no hay sesion. */
  createProforma(): void {
    if (this.saving() || !this.canAct) {
      return;
    }
    if (this.authService.isStaff) {
      const draft = this.buildDraft();
      if (draft && this.authService.hasPermission('add_proforma_header')) {
        this.creating.set(true);
        this.router.navigate(['/ordenes/proformas/create'], { state: draftToState(draft) });
      }
      return;
    }
    this.saveAsClient();
  }

  private async saveAsClient(): Promise<void> {
    this.saveError.set('');
    this.creating.set(true);
    if (!this.authService.isClient) {
      const ok = await this.accesoModal.open('login', 'Inicia sesión o crea tu cuenta para guardar tu proforma.');
      if (!ok) {
        this.creating.set(false);
        return;
      }
      if (this.authService.isStaff) {
        this.creating.set(false);
        this.saveError.set('Las proformas de personal se crean desde el panel de Órdenes.');
        return;
      }
    }
    this.submitInvoice();
  }

  private submitInvoice(): void {
    this.saving.set(true);
    this.clienteService
      .me()
      .pipe(
        switchMap((profile) => {
          this.profile.set(profile);
          const payload = this.buildInvoice(profile);
          if (!payload) {
            throw new Error('Cotización vacía');
          }
          return this.clienteService.createInvoice(payload);
        })
      )
      .subscribe({
        next: ({ id }) => {
          this.saving.set(false);
          this.toastr.success(`Proforma ${id} guardada`);
          this.router.navigate(['/mis-proformas'], { state: { savedId: id } });
        },
        error: (err: HttpErrorResponse) => {
          this.saving.set(false);
          if (err.status === 401) {
            // La sesion vencio: el evento `sessionExpired$` reabre el modal y reintenta.
            return;
          }
          this.creating.set(false);
          this.saveError.set(
            err.status === 404
              ? 'Tu cuenta no tiene un perfil de cliente. Crea una cuenta para guardar tu proforma.'
              : extractApiError(err, 'No se pudo guardar la proforma. Inténtalo de nuevo.')
          );
        },
      });
  }

  private async onSessionExpired(): Promise<void> {
    if (!this.creating()) {
      return;
    }
    this.saving.set(false);
    const ok = await this.accesoModal.open('login', 'Tu sesión venció. Inicia sesión para guardar tu proforma.');
    if (ok && this.authService.isClient) {
      this.submitInvoice();
    } else {
      this.creating.set(false);
    }
  }
}
