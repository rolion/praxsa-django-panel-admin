import { Route } from '@angular/router';
import { MainLayoutComponent } from './layout/app-layout/main-layout/main-layout.component';
import { AuthGuard } from './core/guard/auth.guard';
import { AuthLayoutComponent } from './layout/app-layout/auth-layout/auth-layout.component';
import { Page404Component } from './authentication/page404/page404.component';

export const APP_ROUTE: Route[] = [
    {
        path: '',
        component: MainLayoutComponent,
        canActivate: [AuthGuard],
        children: [
            { path: '', redirectTo: '/authentication/signin', pathMatch: 'full' },
            {
                path: 'dashboard',
                loadChildren: () =>
                    import('./dashboard/dashboard.routes').then((m) => m.DASHBOARD_ROUTE),
            },
            {
                path: 'advance-table',
                loadChildren: () =>
                    import('./advance-table/advance-table.routes').then(
                        (m) => m.ADVANCE_TABLE_ROUTE
                    ),
            },
            {
                path: 'extra-pages',
                loadChildren: () =>
                    import('./extra-pages/extra-pages.routes').then(
                        (m) => m.EXTRA_PAGES_ROUTE
                    ),
            },
            {
                path: 'multilevel',
                loadChildren: () =>
                    import('./multilevel/multilevel.routes').then(
                        (m) => m.MULTILEVEL_ROUTE
                    ),
            },
            {
                path: 'users',
                loadChildren: () =>
                    import('./users/users.routes').then((m) => m.USERS_ROUTE),
            },
            {
                path: 'vehicles',
                loadChildren: () =>
                    import('./vehicles/vehicles.routes').then((m) => m.VEHICLES_ROUTE),
            },
            {
                path: 'almacen',
                loadChildren: () =>
                    import('./almacen/almacen.routes').then((m) => m.ALMACEN_ROUTE),
            },
            {
                path: 'ordenes',
                loadChildren: () =>
                    import('./ordenes/ordenes.routes').then((m) => m.ORDENES_ROUTE),
            },
            {
                path: 'reportes',
                loadChildren: () =>
                    import('./reportes/reportes.routes').then((m) => m.REPORTES_ROUTE),
            },
        ],
    },
    {
        path: 'authentication',
        component: AuthLayoutComponent,
        loadChildren: () =>
            import('./authentication/auth.routes').then((m) => m.AUTH_ROUTE),
    },
    { path: '**', component: Page404Component },
];
