import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';

import { PdfBuilderService } from './pdf-builder.service';

describe('PdfBuilderService', () => {
  let service: PdfBuilderService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule]
    });
    service = TestBed.inject(PdfBuilderService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
