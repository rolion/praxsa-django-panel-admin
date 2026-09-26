import { Route } from '@angular/router';
import { BrandsListComponent } from './brands/brands-list.component';
import { ModelCreateComponent } from './models/model-create.component';
import { ModelEditComponent } from './models/model-edit.component';
import { ModelViewComponent } from './models/model-view.component';
import { ModelsListComponent } from './models/models-list.component';
import { PartsListComponent } from './parts/parts-list.component';

export const VEHICLES_ROUTE: Route[] = [
  { path: 'brands', component: BrandsListComponent },
  { path: 'models', component: ModelsListComponent },
  { path: 'models/create', component: ModelCreateComponent },
  { path: 'models/view/:id', component: ModelViewComponent },
  { path: 'models/edit/:id', component: ModelEditComponent },
  { path: 'parts', component: PartsListComponent },
];
