import { HTTP_INTERCEPTORS, provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { ApplicationConfig, importProvidersFrom } from '@angular/core';
import { APP_ROUTE } from './app.routes';
import { provideRouter } from '@angular/router';
import { provideAnimations } from '@angular/platform-browser/animations';
import { JwtInterceptor } from '@core/interceptor/jwt.interceptor';
import { ErrorInterceptor } from '@core/interceptor/error.interceptor';
import { DirectionService, LanguageService } from '@core';
import { provideTranslateService } from '@ngx-translate/core';
import { provideTranslateHttpLoader } from '@ngx-translate/http-loader';
import { FeatherModule } from 'angular-feather';
import { allIcons } from 'angular-feather/icons';
import { provideCharts, withDefaultRegisterables } from 'ng2-charts';
import { provideToastr } from 'ngx-toastr';

export const appConfig: ApplicationConfig = {
    providers: [
        // withInterceptorsFromDi() es obligatorio para que los HTTP_INTERCEPTORS
        // clasicos (JwtInterceptor, ErrorInterceptor) de abajo se ejecuten -
        // provideHttpClient() sin esa feature los ignora por completo (bug
        // preexistente de la plantilla: nunca se notaba porque AuthService
        // era 100% mock, sin HTTP real, hasta este modulo de Usuarios).
        provideHttpClient(withInterceptorsFromDi()),
        provideRouter(APP_ROUTE),
        provideToastr(),
        provideAnimations(),
        { provide: HTTP_INTERCEPTORS, useClass: JwtInterceptor, multi: true },
        { provide: HTTP_INTERCEPTORS, useClass: ErrorInterceptor, multi: true },
        DirectionService, LanguageService,
        provideTranslateService({
            defaultLanguage: 'en',
        }),
        provideTranslateHttpLoader({
            prefix: './assets/i18n/',
            suffix: '.json',
        }),
        importProvidersFrom(FeatherModule.pick(allIcons)),
        provideCharts(withDefaultRegisterables()),
    ],
};
