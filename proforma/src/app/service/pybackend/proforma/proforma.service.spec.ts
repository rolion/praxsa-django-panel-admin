import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';

import { ProformaService } from './proforma.service';

describe('ProformaService', () => {
  let service: ProformaService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule]
    });
    service = TestBed.inject(ProformaService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
