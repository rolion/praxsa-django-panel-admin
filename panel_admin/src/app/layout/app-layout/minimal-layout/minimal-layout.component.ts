import { Direction } from '@angular/cdk/bidi';
import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { DirectionService, LocalStorageService } from '@core';
import { HeaderComponent } from '../../header/header.component';

/** Layout sin sidebar ni right-sidebar: solo el header (variante minima, con
 * logo) y el contenido. Lo usa la Calculadora de precios
 * (ADR-pricing-calculator-screen-layout-sin-sidebar). */
@Component({
  selector: 'app-minimal-layout',
  templateUrl: './minimal-layout.component.html',
  imports: [HeaderComponent, RouterOutlet],
})
export class MinimalLayoutComponent {
  direction: Direction = 'ltr';

  private directionService = inject(DirectionService);
  private storageService = inject(LocalStorageService);

  constructor() {
    this.directionService.currentData.subscribe((currentData) => {
      if (currentData) {
        this.direction = currentData === 'ltr' ? 'ltr' : 'rtl';
      } else if (this.storageService.has('isRtl')) {
        this.direction = (this.storageService.get('isRtl') as string) === 'true' ? 'rtl' : 'ltr';
      }
    });
  }
}
