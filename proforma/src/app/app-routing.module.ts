import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Routes } from '@angular/router';
import {FormularioComponent} from './pages/formulario/formulario.component';
import {ProformaComponent} from './pages/proforma/proforma.component';
import {NotfoundComponent} from './components/notfound/notfound.component';
import {PoliticaComponent} from './pages/politica/politica.component';
import {EliminacionDatosComponent} from './pages/eliminacion-datos/eliminacion-datos.component';
import { ListProformaComponent } from './components/invoiceTable/list-proforma.component';
import { LoginPageComponent } from './pages/login-page/login-page.component';
import { NewUserComponent } from './pages/new-user/new-user.component';
import { ListaComponent } from './pages/lista/lista.component';
import { WindowsFilmComponent } from './pages/windows-film/windows-film.component';
import { AuthGuard } from './guards/auth.guard';
// import { HomeV2Component } from './components/home-v2/home-v2.component';

const routes: Routes = [
  { path: '', component: FormularioComponent },
  { path: 'proforma/:id', component: ProformaComponent, canActivate: [AuthGuard]},
  { path: 'politica', component: PoliticaComponent},
  { path: 'eliminacion-datos', component: EliminacionDatosComponent},
  { path: 'create-user', component: NewUserComponent},
  { path: 'login', component: LoginPageComponent},
  { path: 'my-invoice', component: ListaComponent, canActivate: [AuthGuard]},
  { path: 'windows-film/:id', component: WindowsFilmComponent},
  { path: '**', component: NotfoundComponent },
];

@NgModule({
  declarations: [],
  imports: [
    CommonModule,
    RouterModule.forRoot(routes, {
    initialNavigation: 'enabledBlocking'
})
  ],
  exports: [RouterModule]
})
export class AppRoutingModule { }
