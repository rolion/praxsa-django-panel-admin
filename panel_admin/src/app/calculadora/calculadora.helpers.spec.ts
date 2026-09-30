import { AppCarModelPart } from '../vehicles/vehicles.model';
import { ReelCatalogItem } from '../ordenes/ordenes.model';
import {
  buildWhatsappMessage,
  buildWhatsappUrl,
  draftToState,
  filmOptionsFor,
  formatBs,
  isReelEligible,
  parseDraft,
  reelKey,
} from './calculadora.helpers';
import { CotizacionDraft } from './calculadora.model';

const item = (over: Partial<AppCarModelPart> = {}): AppCarModelPart => ({
  id: 1,
  car_part_id: 5,
  car_part_name: 'Parabrisas',
  width: '1.50',
  length: '1.20',
  quantity: 2,
  installation_price: '50.00',
  ...over,
});

const reel = (over: Partial<ReelCatalogItem> = {}): ReelCatalogItem => ({
  window_film: 3,
  window_film_name: 'Carbon',
  width: '1.50',
  available_meters: '50.00',
  unit_price: '120.00',
  ...over,
});

describe('calculadora.helpers', () => {
  describe('reelKey', () => {
    it('normalizes the width to 2 decimals', () => {
      expect(reelKey(3, '1.5')).toBe('3|1.50');
      expect(reelKey(3, 1.5)).toBe('3|1.50');
    });
  });

  describe('isReelEligible', () => {
    it('accepts a reel as wide as the item with enough meters', () => {
      expect(isReelEligible(reel(), item())).toBeTrue();
    });

    it('accepts a wider reel', () => {
      expect(isReelEligible(reel({ width: '1.80' }), item())).toBeTrue();
    });

    it('rejects a narrower reel', () => {
      expect(isReelEligible(reel({ width: '1.00' }), item())).toBeFalse();
    });

    it('requires length x quantity meters (exact is enough, less is not)', () => {
      // 1.20 x 2 = 2.40
      expect(isReelEligible(reel({ available_meters: '2.40' }), item())).toBeTrue();
      expect(isReelEligible(reel({ available_meters: '2.39' }), item())).toBeFalse();
    });
  });

  describe('filmOptionsFor', () => {
    it('keeps only eligible reels, cheapest first', () => {
      const options = filmOptionsFor(
        [
          reel({ window_film: 1, window_film_name: 'Premium', unit_price: '200.00' }),
          reel({ window_film: 2, window_film_name: 'Basica', unit_price: '80.00' }),
          reel({ window_film: 3, window_film_name: 'Angosta', width: '1.00', unit_price: '10.00' }),
        ],
        item()
      );
      expect(options.map((o) => o.name)).toEqual(['Basica', 'Premium']);
      expect(options[0].key).toBe('2|1.50');
      expect(options[0].recommended).toBeUndefined();
    });

    it('returns an empty list when no reel fits', () => {
      expect(filmOptionsFor([reel({ width: '0.50' })], item())).toEqual([]);
    });
  });

  describe('formatBs', () => {
    it('prefixes Bs and uses the es-BO thousands separator without forced decimals', () => {
      expect(formatBs(2090)).toMatch(/^Bs 2\.090$/);
      expect(formatBs(0)).toBe('Bs 0');
    });

    it('keeps up to 2 decimals', () => {
      expect(formatBs(12.5)).toMatch(/^Bs 12,5$/);
    });
  });

  describe('whatsapp', () => {
    it('builds the message with vehicle, items and total', () => {
      const message = buildWhatsappMessage(
        'Toyota Hilux',
        'Central',
        [{ itemName: 'Parabrisas', filmName: 'Carbon', subtotal: 388 }],
        388
      );
      expect(message).toContain('Vehiculo: Toyota Hilux');
      expect(message).toContain('Sucursal: Central');
      expect(message).toContain('- Parabrisas: Carbon (Bs 388)');
      expect(message).toContain('Total referencial: Bs 388');
    });

    it('builds a wa.me url with digits only and an encoded text', () => {
      const url = buildWhatsappUrl('+591 7818-1012', 'Hola mundo\nTotal: Bs 1');
      expect(url.startsWith('https://wa.me/59178181012?text=')).toBeTrue();
      expect(url).toContain(encodeURIComponent('Hola mundo\nTotal: Bs 1'));
    });
  });

  describe('draft', () => {
    const draft: CotizacionDraft = {
      version: 1,
      sucursal: 1,
      carModelId: 9,
      lines: [{ carPartId: 5, windowFilm: 3, width: '1.50', length: '1.20', quantity: 2 }],
    };

    it('round-trips through the navigation state', () => {
      expect(parseDraft(draftToState(draft))).toEqual(draft);
    });

    it('returns null for missing state, other versions and corrupt data', () => {
      expect(parseDraft(null)).toBeNull();
      expect(parseDraft({})).toBeNull();
      expect(parseDraft({ cotizacion: { ...draft, version: 2 } })).toBeNull();
      expect(parseDraft({ cotizacion: { ...draft, sucursal: 'x' } })).toBeNull();
      expect(parseDraft({ cotizacion: { ...draft, lines: [] } })).toBeNull();
      expect(parseDraft({ cotizacion: { ...draft, lines: [{ carPartId: 5 }] } })).toBeNull();
    });
  });
});
