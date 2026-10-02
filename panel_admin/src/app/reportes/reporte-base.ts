import { inject } from '@angular/core';
import { FormControl, FormGroup } from '@angular/forms';
import { Observable } from 'rxjs';
import { AuthService } from '../core/service/auth.service';
import { extractApiError } from '../ordenes/ordenes.errors';
import { OrdenSucursal } from '../ordenes/ordenes.model';
import { OrdenesService } from '../ordenes/ordenes.service';
import { ReporteFiltros } from './reportes.model';
import { bs, fechaHora, hoyIso, porcentaje, rangoInvalido } from './reportes.filtros';

/** Logica comun de las pantallas de reportes: filtros de servidor (rango de fechas, sucursal,
 * tipo de venta), estados de carga/error/sin permiso y sucursales visibles. Ocultar o mostrar
 * segun permiso es solo UX: el servidor responde 403 sin el permiso del reporte (ADR-...-permisos). */
export abstract class ReporteBase<T> {
  protected ordenesService = inject(OrdenesService);
  authService = inject(AuthService);

  /** Permiso Django `view` del reporte (`view_proxy_pagos`, `view_utilidades`). */
  protected abstract readonly permission: string;
  protected abstract defaultDesde(): string;
  protected abstract fetch(filtros: ReporteFiltros): Observable<T>;
  protected abstract loaded(report: T): void;

  readonly bs = bs;
  readonly fechaHora = fechaHora;
  readonly porcentaje = porcentaje;

  filtros = new FormGroup({
    desde: new FormControl('', { nonNullable: true }),
    hasta: new FormControl('', { nonNullable: true }),
    /** Sucursales marcadas en el multiselect; por defecto las activas (ver defaultSucursalIds). */
    sucursales: new FormControl<number[]>([], { nonNullable: true }),
    salesType: new FormControl('', { nonNullable: true }),
    tipoPago: new FormControl('', { nonNullable: true }),
  });
  sucursales: OrdenSucursal[] = [];
  loading = false;
  errorMessage = '';
  rangeError = '';
  withoutSucursal = false;
  loadedOnce = false;

  get canView(): boolean {
    return this.authService.hasPermission(this.permission);
  }

  /** Con varias sucursales (o una inactiva, que hay que poder marcar) se ofrece el multiselect;
   * con una sola activa se muestra fija. */
  get showSucursalSelector(): boolean {
    return this.sucursales.length > 1 || this.sucursales.some((sucursal) => sucursal.activa === false);
  }

  /** Marcadas por defecto: las activas; si todas son inactivas, esas (para no pedir un reporte vacio). */
  protected defaultSucursalIds(): number[] {
    const activas = this.sucursales.filter((sucursal) => sucursal.activa !== false);
    return (activas.length ? activas : this.sucursales).map((sucursal) => sucursal.id);
  }

  protected init(): void {
    if (!this.canView) {
      return;
    }
    this.resetFiltros();
    this.ordenesService.listSucursales().subscribe({
      next: (sucursales) => this.onSucursalesLoaded(sucursales),
      error: () => (this.sucursales = []),
    });
    this.aplicar();
  }

  private onSucursalesLoaded(sucursales: OrdenSucursal[]): void {
    this.sucursales = sucursales;
    const ids = this.defaultSucursalIds();
    this.filtros.controls.sucursales.setValue(ids);
    // Solo inactivas: el servidor (por defecto, "las activas") devolveria vacio; se vuelve a pedir.
    if (ids.length > 0 && sucursales.every((sucursal) => sucursal.activa === false)) {
      this.aplicar();
    }
  }

  private resetFiltros(): void {
    this.filtros.reset({
      desde: this.defaultDesde(), hasta: hoyIso(), sucursales: this.defaultSucursalIds(), salesType: '', tipoPago: '',
    });
  }

  limpiar(): void {
    this.resetFiltros();
    this.aplicar();
  }

  aplicar(): void {
    const { desde, hasta, sucursales, salesType, tipoPago } = this.filtros.getRawValue();
    this.rangeError = rangoInvalido(desde, hasta);
    if (this.rangeError) {
      return;
    }
    this.loading = true;
    this.errorMessage = '';
    this.fetch({
      desde,
      hasta,
      sucursales,
      salesType: salesType as ReporteFiltros['salesType'],
      tipoPago: tipoPago as ReporteFiltros['tipoPago'],
    }).subscribe({
      next: (report) => {
        this.loaded(report);
        this.loading = false;
        this.loadedOnce = true;
      },
      error: (err) => {
        this.errorMessage = extractApiError(err, 'No se pudo cargar el reporte.');
        this.loading = false;
      },
    });
  }
}
