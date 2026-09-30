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
    sucursal: new FormControl<number | null>(null),
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

  /** Con varias sucursales se ofrece el selector ("Todas"); con una sola se muestra fija. */
  get showSucursalSelector(): boolean {
    return this.sucursales.length > 1;
  }

  protected init(): void {
    if (!this.canView) {
      return;
    }
    this.resetFiltros();
    this.ordenesService.listSucursales().subscribe({
      next: (sucursales) => (this.sucursales = sucursales),
      error: () => (this.sucursales = []),
    });
    this.aplicar();
  }

  private resetFiltros(): void {
    this.filtros.reset({ desde: this.defaultDesde(), hasta: hoyIso(), sucursal: null, salesType: '', tipoPago: '' });
  }

  limpiar(): void {
    this.resetFiltros();
    this.aplicar();
  }

  aplicar(): void {
    const { desde, hasta, sucursal, salesType, tipoPago } = this.filtros.getRawValue();
    this.rangeError = rangoInvalido(desde, hasta);
    if (this.rangeError) {
      return;
    }
    this.loading = true;
    this.errorMessage = '';
    this.fetch({
      desde,
      hasta,
      sucursal,
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
