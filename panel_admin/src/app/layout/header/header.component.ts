import { DOCUMENT } from '@angular/common';
import {
  Component,
  ElementRef,
  computed,
  OnInit,
  Renderer2,
  AfterViewInit,
  inject,
  input
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { NgbDropdown, NgbDropdownToggle, NgbDropdownMenu } from '@ng-bootstrap/ng-bootstrap';
import { FeatherModule } from 'angular-feather';
import { AuthService, InConfiguration, LanguageService, LocalStorageService, RightSidebarService } from '@core';
import { ConfigService } from '@config/config.service';
import { AccesoModalService } from '../../cliente/acceso-modal.service';
import { AccesoMode } from '../../cliente/cliente.model';


@Component({
    selector: 'app-header',
    templateUrl: './header.component.html',
    styleUrls: ['./header.component.sass'],
    imports: [
        FeatherModule,
        NgbDropdown,
        NgbDropdownToggle,
        NgbDropdownMenu,
        RouterLink,
        RouterLinkActive,
    ],
    providers: [RightSidebarService]
})
export class HeaderComponent implements OnInit, AfterViewInit {
  public config!: InConfiguration;
  isNavbarCollapsed = true;
  isOpenSidebar?: boolean;
  docElement?: HTMLElement;
  isFullScreen = false;
  /** Variante sin sidebar (layout minimo): muestra el logo y oculta el toggle del menu lateral. */
  minimal = input(false);

  private document = inject(DOCUMENT);
  private renderer = inject(Renderer2);
  public elementRef = inject(ElementRef);
  private rightSidebarService = inject(RightSidebarService);
  private configService = inject(ConfigService);
  private authService = inject(AuthService);
  private router = inject(Router);
  private storageService = inject(LocalStorageService);
  // Instanciarlo aplica el idioma inicial (navegador/localStorage) que usa el sidebar.
  private languageService = inject(LanguageService);
  private accesoModal = inject(AccesoModalService);

  /** Estado de sesion reactivo (la variante minima cambia segun anonimo / cliente / staff). */
  private session = toSignal(this.authService.currentUser, { initialValue: this.authService.currentUserValue });
  isLoggedIn = computed(() => !!this.session()?.token);
  isStaff = computed(() => this.isLoggedIn() && this.session()?.isStaff === true);

  ngOnInit() {
    this.config = this.configService.configData;
    this.docElement = this.document.documentElement;
  }
  ngAfterViewInit() {
    // set theme on startup
    if (this.storageService.has('theme')) {
      this.renderer.removeClass(this.document.body, this.config.layout.variant);
      this.renderer.addClass(
        this.document.body,
        this.storageService.get('theme') as string
      );
    } else {
      this.renderer.addClass(this.document.body, this.config.layout.variant);
    }

    if (this.storageService.has('menuOption')) {
      this.renderer.addClass(
        this.document.body,
        this.storageService.get('menuOption') as string
      );
    } else {
      this.renderer.addClass(
        this.document.body,
        this.config.layout.sidebar.backgroundColor + '-sidebar'
      );
    }

    if (localStorage.getItem('sidebar_status')) {
      if (localStorage.getItem('sidebar_status') === 'close') {
        this.renderer.addClass(this.document.body, 'side-closed');
        this.renderer.addClass(this.document.body, 'submenu-closed');
      } else {
        this.renderer.removeClass(this.document.body, 'side-closed');
        this.renderer.removeClass(this.document.body, 'submenu-closed');
      }
    } else {
      if (this.config.layout.sidebar.collapsed === true) {
        this.renderer.addClass(this.document.body, 'side-closed');
        this.renderer.addClass(this.document.body, 'submenu-closed');
      }
    }
  }
  callFullscreen() {
    if (!this.isFullScreen) {
      if (this.docElement?.requestFullscreen != null) {
        this.docElement?.requestFullscreen();
      }
    } else {
      document.exitFullscreen();
    }
    this.isFullScreen = !this.isFullScreen;
  }
  get currentUserName(): string {
    return this.authService.currentUserValue.firstName || this.authService.currentUserValue.username;
  }
  mobileMenuSidebarOpen(event: Event, className: string) {
    if (window.innerWidth < 1025) {
      const hasClass = (event.target as HTMLInputElement).classList.contains(
        className
      );
      if (hasClass) {
        this.renderer.removeClass(this.document.body, className);
        this.renderer.addClass(this.document.body, 'sidebar-gone');
      } else {
        this.renderer.addClass(this.document.body, className);
        this.renderer.removeClass(this.document.body, 'sidebar-gone');
      }
    } else {
      const hasClass = this.document.body.classList.contains('side-closed');
      if (hasClass) {
        this.renderer.removeClass(this.document.body, 'side-closed');
        this.renderer.removeClass(this.document.body, 'submenu-closed');
      } else {
        this.renderer.addClass(this.document.body, 'side-closed');
        this.renderer.addClass(this.document.body, 'submenu-closed');
      }
    }
  }
  public toggleRightSidebar(): void {
    this.rightSidebarService.sidebarState.subscribe((isRunning) => {
      this.isOpenSidebar = isRunning;
    });

    this.rightSidebarService.setRightSidebar(
      (this.isOpenSidebar = !this.isOpenSidebar)
    );
  }
  logout() {
    const wasStaff = this.authService.isStaff;
    this.authService.logout();
    // Un cliente vuelve a la calculadora (publica); el staff, al login del panel.
    this.router.navigate([this.minimal() && !wasStaff ? '/calculadora' : '/authentication/signin']);
  }

  /** Abre el modal de acceso; si quien entra es staff va al panel. */
  openAcceso(mode: AccesoMode): void {
    this.accesoModal.open(mode).then((ok) => {
      if (ok && this.authService.isStaff) {
        this.router.navigate(['/dashboard/main']);
      }
    });
  }
}
