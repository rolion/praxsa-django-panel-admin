import { TestBed } from '@angular/core/testing';
import { AppCarModelPart } from '../vehicles.model';
import { ModelItemCardComponent } from './model-item-card.component';

const sampleItem: AppCarModelPart = {
  id: 9,
  car_part_id: 2,
  car_part_name: 'Parabrisas',
  width: '1.2',
  length: '0.8',
  quantity: 2,
  installation_price: '50.00',
};

describe('ModelItemCardComponent', () => {
  function create() {
    const fixture = TestBed.createComponent(ModelItemCardComponent);
    fixture.componentRef.setInput('item', sampleItem);
    fixture.detectChanges();
    return fixture;
  }

  beforeEach(() => TestBed.configureTestingModule({ imports: [ModelItemCardComponent] }));

  it('muestra el nombre de la parte', () => {
    const el = create().nativeElement as HTMLElement;
    expect(el.querySelector('[data-test="item-name"]')?.textContent?.trim()).toBe('Parabrisas');
  });

  it('formatea las dimensiones con 2 decimales y unidad', () => {
    const el = create().nativeElement as HTMLElement;
    const details = el.querySelector('[data-test="item-details"]')?.textContent?.replace(/\s+/g, ' ').trim();
    expect(details).toBe('Dimensiones: Ancho: 1.20m x Largo: 0.80m | Cantidad: 2');
  });

  it('emite edit y remove con el item al hacer clic', () => {
    const fixture = create();
    const edited: AppCarModelPart[] = [];
    const removed: AppCarModelPart[] = [];
    fixture.componentInstance.edit.subscribe((i) => edited.push(i));
    fixture.componentInstance.remove.subscribe((i) => removed.push(i));
    const el = fixture.nativeElement as HTMLElement;

    (el.querySelector('button[title="Editar"]') as HTMLButtonElement).click();
    (el.querySelector('button[title="Quitar"]') as HTMLButtonElement).click();

    expect(edited).toEqual([sampleItem]);
    expect(removed).toEqual([sampleItem]);
  });
});
