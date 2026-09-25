import { Route } from '@angular/router';
import { UsersListComponent } from './list/users-list.component';
import { UserViewComponent } from './view/user-view.component';
import { UserEditComponent } from './edit/user-edit.component';
import { UserCreateComponent } from './create/user-create.component';
import { GroupsListComponent } from './groups/groups-list.component';
import { RolesListComponent } from './roles/roles-list.component';
import { SucursalesListComponent } from './sucursales/sucursales-list.component';

export const USERS_ROUTE: Route[] = [
  { path: '', component: UsersListComponent },
  { path: 'create', component: UserCreateComponent },
  { path: 'view/:id', component: UserViewComponent },
  { path: 'edit/:id', component: UserEditComponent },
  { path: 'groups', component: GroupsListComponent },
  { path: 'roles', component: RolesListComponent },
  { path: 'sucursales', component: SucursalesListComponent },
];
