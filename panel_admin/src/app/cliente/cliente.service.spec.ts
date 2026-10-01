import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../environments/environment';
import { InvoicePayload, RegisterPayload } from './cliente.model';
import { ClienteService } from './cliente.service';

const base = `${environment.apiUrl}/product`;

describe('ClienteService', () => {
  let service: ClienteService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(ClienteService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('registers with POST client/register', () => {
    const payload: RegisterPayload = {
      name: 'Ana', lastname: 'Gomez', email: 'a@b.com', phone_number: '70000001', car_plate: 'ABC123', username: 'ana', password: 'x',
    };
    service.register(payload).subscribe((res) => expect(res).toEqual({ username: 'ana' }));
    const req = httpMock.expectOne(`${base}/client/register`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(payload);
    req.flush({ username: 'ana' });
  });

  it('reads the profile with GET client/me', () => {
    service.me().subscribe();
    const req = httpMock.expectOne(`${base}/client/me`);
    expect(req.request.method).toBe('GET');
    req.flush({});
  });

  it('lists own proformas with GET client/proformas', () => {
    service.proformas().subscribe((rows) => expect(rows.length).toBe(1));
    const req = httpMock.expectOne(`${base}/client/proformas`);
    expect(req.request.method).toBe('GET');
    req.flush([{ id: 1 }]);
  });

  it('saves an invoice with POST invoice (no trailing slash, as the backend route)', () => {
    const payload = { name: 'Ana Gomez', carPartItems: [] } as unknown as InvoicePayload;
    service.createInvoice(payload).subscribe((res) => expect(res.id).toBe(9));
    const req = httpMock.expectOne(`${base}/invoice`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toBe(payload);
    req.flush({ id: 9 });
  });
});
