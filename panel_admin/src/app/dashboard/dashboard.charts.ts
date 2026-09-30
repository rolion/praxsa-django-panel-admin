/** Configuracion de las graficas del dashboard (ApexCharts) como funciones puras, para
 * probarla sin renderizar. `Number(...)` solo se usa para PINTAR series: los importes y
 * metros siguen siendo texto decimal del servidor y no se calcula dinero en el cliente. */
import {
  ApexAxisChartSeries,
  ApexChart,
  ApexDataLabels,
  ApexGrid,
  ApexLegend,
  ApexMarkers,
  ApexNonAxisChartSeries,
  ApexPlotOptions,
  ApexStroke,
  ApexTooltip,
  ApexXAxis,
  ApexYAxis,
} from 'ng-apexcharts';
import { ConsumoLaminas, ItemsSolicitados, ProformasVsVentas } from './dashboard.model';

export interface AxisChartOptions {
  series: ApexAxisChartSeries;
  chart: ApexChart;
  xaxis: ApexXAxis;
  yaxis: ApexYAxis;
  stroke: ApexStroke;
  colors: string[];
  dataLabels: ApexDataLabels;
  legend: ApexLegend;
  tooltip: ApexTooltip;
  markers: ApexMarkers;
  grid: ApexGrid;
  plotOptions: ApexPlotOptions;
}

export interface DonutChartOptions {
  series: ApexNonAxisChartSeries;
  chart: ApexChart;
  labels: string[];
  colors: string[];
  legend: ApexLegend;
  dataLabels: ApexDataLabels;
  plotOptions: ApexPlotOptions;
  tooltip: ApexTooltip;
}

/** Gris medio: legible sobre fondo claro y oscuro (las graficas de la plantilla usan el mismo). */
const FORE_COLOR = '#9aa0ac';
const COLOR_OTROS = '#9aa0ac';
const COLOR_COTIZADO = '#3f51b5';
const COLOR_VENDIDO = '#26a69a';
const PALETA = ['#3f51b5', '#26a69a', '#ff9800', '#e91e63', '#8bc34a', '#9c27b0', '#00bcd4', '#795548'];
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

/** "2026-09" -> "sep 26". */
export function mesLabel(clave: string): string {
  const m = /^(\d{4})-(\d{2})$/.exec(clave);
  if (!m) {
    return clave;
  }
  return `${MESES[Number(m[2]) - 1] ?? m[2]} ${m[1].slice(2)}`;
}

/** Color estable por nombre: la misma lamina/item tiene siempre el mismo color entre visitas. */
export function colorFor(nombre: string): string {
  if (nombre === 'Otras' || nombre === 'Otros') {
    return COLOR_OTROS;
  }
  let hash = 0;
  for (const char of nombre) {
    hash = (hash * 31 + char.charCodeAt(0)) % 9973;
  }
  return PALETA[hash % PALETA.length];
}

/** 12345.5 -> "12.345,5" (es). */
export function numero(value: number, decimales = 2): string {
  return value.toLocaleString('es', { maximumFractionDigits: decimales });
}

/** Abrevia el eje Y: 1500 -> "1,5 k". */
function abreviar(value: number): string {
  return Math.abs(value) >= 1000 ? `${numero(value / 1000, 1)} k` : numero(value, 0);
}

function baseAxis(height = 320): Pick<AxisChartOptions, 'dataLabels' | 'grid' | 'markers'> & { chart: Omit<ApexChart, 'type'> } {
  return {
    chart: { height, foreColor: FORE_COLOR, toolbar: { show: false }, zoom: { enabled: false }, fontFamily: 'inherit' },
    dataLabels: { enabled: false },
    grid: { borderColor: 'rgba(128,128,128,0.2)', strokeDashArray: 3 },
    markers: { size: 3 },
  };
}

/** Linea "Proformas cotizadas vs. ventas reales": 2 series, o 1 si el servidor no entrego las ventas. */
export function lineChart(data: ProformasVsVentas): AxisChartOptions {
  const base = baseAxis();
  const series: ApexAxisChartSeries = [{ name: 'Cotizado', data: data.cotizado.map(Number) }];
  const colors = [COLOR_COTIZADO];
  if (data.vendido !== null) {
    series.push({ name: 'Ventas reales', data: data.vendido.map(Number) });
    colors.push(COLOR_VENDIDO);
  }
  return {
    ...base,
    series,
    chart: { ...base.chart, type: 'line' },
    colors,
    stroke: { curve: 'smooth', width: 3 },
    xaxis: { categories: data.meses.map(mesLabel), labels: { rotate: -45 } },
    yaxis: { labels: { formatter: (v: number) => abreviar(v) } },
    legend: { show: true, position: 'top' },
    tooltip: { shared: true, y: { formatter: (v: number) => `${numero(v)} Bs` } },
    plotOptions: {},
  };
}

/** Barras apiladas de metros por lamina y mes; color fijo por nombre. */
export function stackedBarChart(data: ConsumoLaminas): AxisChartOptions {
  const base = baseAxis();
  return {
    ...base,
    series: data.series.map((s) => ({ name: s.nombre, data: s.metros.map(Number) })),
    chart: { ...base.chart, type: 'bar', stacked: true },
    colors: data.series.map((s) => colorFor(s.nombre)),
    stroke: { width: 0 },
    xaxis: { categories: data.meses.map(mesLabel), labels: { rotate: -45 } },
    yaxis: { title: { text: 'Metros' }, labels: { formatter: (v: number) => numero(v, 0) } },
    legend: { show: true, position: 'top' },
    tooltip: { shared: true, intersect: false, y: { formatter: (v: number) => `${numero(v)} m` } },
    plotOptions: { bar: { columnWidth: '55%', borderRadius: 2 } },
  };
}

/** Donut de items mas solicitados con el total al centro. */
export function donutChart(data: ItemsSolicitados): DonutChartOptions {
  return {
    series: data.items.map((i) => i.cantidad),
    labels: data.items.map((i) => i.nombre),
    colors: data.items.map((i) => colorFor(i.nombre)),
    chart: { type: 'donut', height: 300, foreColor: FORE_COLOR, fontFamily: 'inherit' },
    legend: { show: true, position: 'bottom' },
    dataLabels: { enabled: false },
    tooltip: { y: { formatter: (v: number) => `${numero(v, 0)} líneas` } },
    plotOptions: {
      pie: {
        donut: { size: '68%', labels: { show: true, total: { show: true, label: 'Total', formatter: () => String(data.total) } } },
      },
    },
  };
}
