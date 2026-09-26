import { Route } from '@angular/router';
import { BobinasListComponent } from './bobinas/bobinas-list.component';
import { InventarioListComponent } from './inventario/inventario-list.component';
import { LaminaCreateComponent } from './laminas/lamina-create.component';
import { LaminaEditComponent } from './laminas/lamina-edit.component';
import { LaminaViewComponent } from './laminas/lamina-view.component';
import { LaminasListComponent } from './laminas/laminas-list.component';

export const ALMACEN_ROUTE: Route[] = [
  { path: 'laminas', component: LaminasListComponent },
  { path: 'laminas/create', component: LaminaCreateComponent },
  { path: 'laminas/view/:id', component: LaminaViewComponent },
  { path: 'laminas/edit/:id', component: LaminaEditComponent },
  { path: 'bobinas', component: BobinasListComponent },
  { path: 'inventario', component: InventarioListComponent },
];
