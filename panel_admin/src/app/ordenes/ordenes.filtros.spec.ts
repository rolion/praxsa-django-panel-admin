import { dentroDeRango, opcionesPorId, opcionesUnicas, rangoFechasInvalido, valorDeEvento } from './ordenes.filtros';

describe('ordenes.filtros', () => {
  describe('opcionesUnicas', () => {
    it('returns unique, non empty values sorted alphabetically', () => {
      const rows = [{ m: 'Toyota' }, { m: 'Audi' }, { m: null }, { m: '' }, { m: 'Toyota' }, { m: undefined }];
      expect(opcionesUnicas(rows, (r) => r.m)).toEqual(['Audi', 'Toyota']);
    });

    it('returns an empty list without rows', () => {
      expect(opcionesUnicas([], (r: { m: string }) => r.m)).toEqual([]);
    });
  });

  describe('opcionesPorId', () => {
    it('returns unique options by id sorted by label, skipping null ids', () => {
      const rows = [
        { id: 2, n: 'Norte' }, { id: 1, n: 'Central' }, { id: 2, n: 'Norte' }, { id: null, n: 'x' }, { id: 3, n: null },
      ];
      expect(opcionesPorId(rows, (r) => r.id, (r) => r.n)).toEqual([
        { value: '3', label: '#3' },
        { value: '1', label: 'Central' },
        { value: '2', label: 'Norte' },
      ].sort((a, b) => a.label.localeCompare(b.label, 'es')));
    });
  });

  describe('rangoFechasInvalido', () => {
    it('is valid with an empty or a single extreme and when desde <= hasta', () => {
      expect(rangoFechasInvalido('', '')).toBe('');
      expect(rangoFechasInvalido('2026-09-01', '')).toBe('');
      expect(rangoFechasInvalido('', '2026-09-30')).toBe('');
      expect(rangoFechasInvalido('2026-09-30', '2026-09-30')).toBe('');
    });

    it('reports desde > hasta', () => {
      expect(rangoFechasInvalido('2026-10-01', '2026-09-30')).toContain('inicial');
    });
  });

  describe('dentroDeRango', () => {
    it('passes everything without an active range, even null dates', () => {
      expect(dentroDeRango('2026-09-30T10:00:00', '', '')).toBe(true);
      expect(dentroDeRango(null, '', '')).toBe(true);
    });

    it('has inclusive limits and compares only the date part', () => {
      expect(dentroDeRango('2026-09-01T00:00:00', '2026-09-01', '2026-09-30')).toBe(true);
      expect(dentroDeRango('2026-09-30T23:59:59', '2026-09-01', '2026-09-30')).toBe(true);
      expect(dentroDeRango('2026-08-31T23:59:59', '2026-09-01', '2026-09-30')).toBe(false);
      expect(dentroDeRango('2026-10-01T00:00:00', '2026-09-01', '2026-09-30')).toBe(false);
    });

    it('supports a single extreme', () => {
      expect(dentroDeRango('2026-09-15', '2026-09-10', '')).toBe(true);
      expect(dentroDeRango('2026-09-05', '2026-09-10', '')).toBe(false);
      expect(dentroDeRango('2026-09-05', '', '2026-09-10')).toBe(true);
      expect(dentroDeRango('2026-09-15', '', '2026-09-10')).toBe(false);
    });

    it('excludes null dates only when a range is active', () => {
      expect(dentroDeRango(null, '2026-09-01', '')).toBe(false);
      expect(dentroDeRango(undefined, '', '2026-09-30')).toBe(false);
    });

    it('does not filter by date when the range is invalid', () => {
      expect(dentroDeRango('2026-01-01', '2026-10-01', '2026-09-30')).toBe(true);
    });
  });

  it('valorDeEvento reads the value of the event target', () => {
    expect(valorDeEvento({ target: { value: '7' } } as unknown as Event)).toBe('7');
  });
});
