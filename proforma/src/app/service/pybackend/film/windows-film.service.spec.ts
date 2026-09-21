import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';

import { WindowsFilmService } from './windows-film.service';

describe('WindowsFilmService', () => {
  let service: WindowsFilmService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule]
    });
    service = TestBed.inject(WindowsFilmService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
