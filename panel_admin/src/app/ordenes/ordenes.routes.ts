import { Route } from '@angular/router';
import { NotaTrabajoViewComponent } from './notas-trabajo/nota-trabajo-view.component';
import { NotasTrabajoListComponent } from './notas-trabajo/notas-trabajo-list.component';
import { NotaVentaViewComponent } from './notas-venta/nota-venta-view.component';
import { NotasVentaListComponent } from './notas-venta/notas-venta-list.component';
import { ProformaFormComponent } from './proformas/proforma-form.component';
import { ProformaViewComponent } from './proformas/proforma-view.component';
import { ProformasListComponent } from './proformas/proformas-list.component';

export const ORDENES_ROUTE: Route[] = [
  { path: 'proformas', component: ProformasListComponent },
  { path: 'proformas/create', component: ProformaFormComponent },
  { path: 'proformas/view/:id', component: ProformaViewComponent },
  { path: 'proformas/edit/:id', component: ProformaFormComponent },
  { path: 'notas-trabajo', component: NotasTrabajoListComponent },
  { path: 'notas-trabajo/view/:id', component: NotaTrabajoViewComponent },
  // La edicion es in-situ: la misma vista, abierta ya en modo edicion.
  { path: 'notas-trabajo/edit/:id', component: NotaTrabajoViewComponent, data: { edit: true } },
  { path: 'notas-venta', component: NotasVentaListComponent },
  { path: 'notas-venta/view/:id', component: NotaVentaViewComponent },
];
