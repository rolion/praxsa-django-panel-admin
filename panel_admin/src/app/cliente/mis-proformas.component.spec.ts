import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { environment } from '../../environments/environment';
import { ClientProformaRow } from './cliente.model';
import { MisProformasComponent } from './mis-proformas.component';

const url = `${environment.apiUrl}/product/client/proformas`;

const rows: ClientProformaRow[] = [
  { id: 3, date: '2026-09-28T14:05:00-04:00', car_brand_name: 'Toyota', car_model_name: 'Hilux', car_plate: 'ABC123', total_price: '2090.00' },
  { id: 5, date: '2026-09-30T09:30:00-04:00', car_brand_name: 'Kia', car_model_name: 'Rio', car_plate: '', total_price: '950.50' },
];

describe('MisProformasComponent', () => {
  let fixture: ComponentFixture<MisProformasComponent>;
  let component: MisProformasComponent;
  let httpMock: HttpTestingController;

  function setup() {
    TestBed.configureTestingModule({
      imports: [MisProformasComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    httpMock = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(MisProformasComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  const el = () => fixture.nativeElement as HTMLElement;

  afterEach(() => {
    httpMock.verify();
    history.replaceState(null, '');
  });

  it('shows a skeleton while loading', () => {
    setup();
    expect(el().querySelector('[data-state="loading"]')).not.toBeNull();
    httpMock.expectOne(url).flush([]);
  });

  it('shows the empty state with a link back to the calculator', () => {
    setup();
    httpMock.expectOne(url).flush([]);
    fixture.detectChanges();
    expect(el().querySelector('[data-state="empty"]')?.textContent).toContain('Aún no tienes proformas');
    expect(el().querySelector('[data-state="empty"] a')?.getAttribute('href')).toContain('calculadora');
  });

  it('shows the error state and retries', () => {
    setup();
    httpMock.expectOne(url).flush('x', { status: 500, statusText: 'err' });
    fixture.detectChanges();
    expect(el().querySelector('[data-state="error"]')?.textContent).toContain('No se pudieron cargar tus proformas');

    component.load();
    httpMock.expectOne(url).flush(rows);
    fixture.detectChanges();
    expect(el().querySelector('[data-state="list"]')).not.toBeNull();
  });

  it('lists the proformas newest first in a read-only table (no actions)', () => {
    setup();
    httpMock.expectOne(url).flush(rows);
    fixture.detectChanges();

    expect(component.rows().map((r) => r.id)).toEqual([5, 3]);
    const table = el().querySelector('[data-state="list"]') as HTMLElement;
    const headers = Array.from(table.querySelectorAll('.datatable-header-cell-label')).map((h) => h.textContent?.trim());
    expect(headers).toEqual(['Nº', 'Fecha', 'Vehículo', 'Placa', 'Total']);
    expect(table.querySelector('button')).toBeNull();
    expect(table.querySelector('a')).toBeNull();
    const body = table.textContent ?? '';
    expect(body).toContain('Kia Rio');
    expect(body).toContain('Toyota Hilux');
    expect(body).toContain('Bs 2.090');
    expect(body).toContain('Bs 950,5');
    expect(body).toContain('30/09/2026');
    expect(body).toContain('28/09/2026');
  });

  it('shows "—" for a missing plate', () => {
    setup();
    httpMock.expectOne(url).flush(rows);
    fixture.detectChanges();
    expect(el().textContent).toContain('—');
  });

  it('highlights the proforma just saved (navigation state) and stops after a while', () => {
    history.replaceState({ savedId: 5 }, '');
    setup();
    httpMock.expectOne(url).flush(rows);
    fixture.detectChanges();
    expect(component.highlightedId()).toBe(5);
    expect(component.rowClass(rows[1])).toEqual({ 'saved-row': true });
    expect(component.rowClass(rows[0])).toEqual({ 'saved-row': false });
    component.ngOnDestroy();
  });

  it('does not highlight anything without navigation state', () => {
    setup();
    httpMock.expectOne(url).flush(rows);
    expect(component.highlightedId()).toBeNull();
  });
});
