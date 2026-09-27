import { Route } from '@angular/router';
import { BobinasListComponent } from './bobinas/bobinas-list.component';
import { InventarioCreateComponent } from './inventario/inventario-create.component';
import { InventarioEditComponent } from './inventario/inventario-edit.component';
import { InventarioListComponent } from './inventario/inventario-list.component';
import { InventarioViewComponent } from './inventario/inventario-view.component';
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
  { path: 'inventario/create', component: InventarioCreateComponent },
  { path: 'inventario/view/:id', component: InventarioViewComponent },
  { path: 'inventario/edit/:id', component: InventarioEditComponent },
];
