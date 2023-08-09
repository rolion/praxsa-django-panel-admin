import { TestBed } from '@angular/core/testing';

import { WindowsFilmService } from './windows-film.service';

describe('WindowsFilmService', () => {
  let service: WindowsFilmService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(WindowsFilmService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
