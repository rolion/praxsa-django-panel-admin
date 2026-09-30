import { Route } from '@angular/router';
import { UtilidadComponent } from './utilidad/utilidad.component';
import { VentasDiariasComponent } from './ventas-diarias/ventas-diarias.component';

export const REPORTES_ROUTE: Route[] = [
  { path: 'ventas-diarias', component: VentasDiariasComponent },
  { path: 'utilidad', component: UtilidadComponent },
];
