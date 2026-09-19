import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';

import { AutheticationService } from './authetication.service';

describe('AutheticationService', () => {
  let service: AutheticationService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule]
    });
    service = TestBed.inject(AutheticationService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
