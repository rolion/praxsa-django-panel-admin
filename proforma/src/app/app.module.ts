import { NgModule } from '@angular/core';
import { BrowserModule , provideClientHydration} from '@angular/platform-browser';
import { AppComponent } from './app.component';
import { NgbModule } from '@ng-bootstrap/ng-bootstrap';
import {TopMenuComponent} from "./components/top-menu/top-menu.component";
import {FormularioComponent} from "./pages/formulario/formulario.component";
import {NgModalContentComponent} from "./components/ng-modal-content/ng-modal-content.component";
import {ProformaComponent} from "./pages/proforma/proforma.component";
import {NotfoundComponent} from "./components/notfound/notfound.component";
import {PoliticaComponent} from "./pages/politica/politica.component";
import {EliminacionDatosComponent} from "./pages/eliminacion-datos/eliminacion-datos.component";
import {HTTP_INTERCEPTORS, HttpClientModule, HttpClientXsrfModule} from "@angular/common/http";
import {AppRoutingModule} from "./app-routing.module";
import {FormsModule, ReactiveFormsModule} from "@angular/forms";
import {FontAwesomeModule} from "@fortawesome/angular-fontawesome";
import { HashLocationStrategy, LocationStrategy} from "@angular/common";
import { CreateUserComponent } from './components/create-user/create-user.component';
import { LoginComponent } from './components/login/login.component';
import { AuthInterceptor } from './app-http-interceptor';
import { ListProformaComponent } from './components/invoiceTable/list-proforma.component';
import { DataTablesModule } from 'angular-datatables';
import { LoginPageComponent } from './pages/login-page/login-page.component';
import { NewUserComponent } from './pages/new-user/new-user.component';
import { ListaComponent } from './pages/lista/lista.component';
import { BannerComponent } from './components/banner/banner.component';

@NgModule({
  declarations: [
    AppComponent,
    TopMenuComponent,
    FormularioComponent,
    NgModalContentComponent,
    ProformaComponent,
    NotfoundComponent,
    PoliticaComponent,
    EliminacionDatosComponent,
    CreateUserComponent,
    LoginComponent,
    ListProformaComponent,
    LoginPageComponent,
    NewUserComponent,
    ListaComponent,
    BannerComponent
  ],
  imports: [
    BrowserModule,
    NgbModule,
    FontAwesomeModule,
    AppRoutingModule,
    NgbModule,
    HttpClientModule,
    HttpClientXsrfModule,
    FormsModule,
    ReactiveFormsModule,
    DataTablesModule
  ],
  providers: [
    {provide: LocationStrategy, useClass: HashLocationStrategy},
    { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true },
    provideClientHydration(),

  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
