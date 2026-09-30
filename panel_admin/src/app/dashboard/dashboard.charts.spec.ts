import { colorFor, donutChart, lineChart, mesLabel, numero, stackedBarChart } from './dashboard.charts';
import { ConsumoLaminas, ItemsSolicitados, ProformasVsVentas } from './dashboard.model';

const base = { generado: '2026-09-30T10:00:00', sucursal: null };

describe('dashboard charts', () => {
  const serie = (vendido: string[] | null): ProformasVsVentas => ({
    ...base, meses: ['2026-08', '2026-09'], cotizado: ['100.00', '250.50'], vendido,
  });

  it('labels the months in Spanish', () => {
    expect(mesLabel('2026-09')).toBe('sep 26');
    expect(mesLabel('2026-01')).toBe('ene 26');
    expect(mesLabel('raro')).toBe('raro');
  });

  it('draws two series when the server sends the sales', () => {
    const o = lineChart(serie(['80.00', '90.25']));
    expect(o.series.map((s) => s.name)).toEqual(['Cotizado', 'Ventas reales']);
    expect(o.series[1].data).toEqual([80, 90.25]);
    expect(o.colors.length).toBe(2);
    expect(o.xaxis.categories).toEqual(['ago 26', 'sep 26']);
  });

  it('draws only the quoted series when the sales come null (no permission)', () => {
    const o = lineChart(serie(null));
    expect(o.series.map((s) => s.name)).toEqual(['Cotizado']);
    expect(o.colors.length).toBe(1);
  });

  it('formats tooltips with the currency and the thousands separator', () => {
    const formatter = lineChart(serie(null)).tooltip.y as { formatter: (v: number) => string };
    expect(formatter.formatter(1234.5)).toBe(`${numero(1234.5)} Bs`);
  });

  it('builds a stacked bar with one series per lamina and stable colors', () => {
    const consumo: ConsumoLaminas = {
      ...base, meses: ['2026-08', '2026-09'],
      series: [
        { nombre: 'Ceramica', metros: ['1.00', '4.50'], total: '5.50' },
        { nombre: 'Otras', metros: ['0.00', '2.00'], total: '2.00' },
      ],
    };
    const o = stackedBarChart(consumo);
    expect(o.chart.type).toBe('bar');
    expect(o.chart.stacked).toBe(true);
    expect(o.series[0].data).toEqual([1, 4.5]);
    expect(o.colors[0]).toBe(colorFor('Ceramica'));
    expect(o.colors[1]).toBe(colorFor('Otras'));
  });

  it('gives the same color to the same name and a neutral one to the grouped rest', () => {
    expect(colorFor('Seguridad 8mil')).toBe(colorFor('Seguridad 8mil'));
    expect(colorFor('Otras')).toBe(colorFor('Otros'));
    expect(colorFor('Otras')).not.toBe(colorFor('Ceramica'));
  });

  it('builds a donut with the total in the center', () => {
    const items: ItemsSolicitados = {
      ...base, total: 6, items: [{ nombre: 'Parabrisas', cantidad: 4 }, { nombre: 'Laterales', cantidad: 2 }],
    };
    const o = donutChart(items);
    expect(o.chart.type).toBe('donut');
    expect(o.series).toEqual([4, 2]);
    expect(o.labels).toEqual(['Parabrisas', 'Laterales']);
    const total = o.plotOptions.pie?.donut?.labels?.total;
    expect((total?.formatter as () => string)()).toBe('6');
  });
});
