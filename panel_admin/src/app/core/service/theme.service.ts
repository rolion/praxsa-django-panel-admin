import { DOCUMENT } from '@angular/common';
import { Injectable, RendererFactory2, inject, signal } from '@angular/core';
import { ConfigService } from '@config/config.service';

export type ThemeMode = 'light' | 'dark';

const SKINS = ['white', 'cyan', 'black', 'purple', 'orange', 'green', 'red'];

/**
 * Modo claro/oscuro del panel de staff. Escribe las claves sin prefijo
 * (`theme`, `menuOption`, `choose_skin`) que ya usaba el panel de ajustes;
 * no usa `LocalStorageService` porque ese antepone `light_`/`dark_` al leer.
 */
@Injectable({
  providedIn: 'root',
})
export class ThemeService {
  private document = inject(DOCUMENT);
  private renderer = inject(RendererFactory2).createRenderer(null, null);
  private configService = inject(ConfigService);

  readonly isDark = signal(false);

  /** Aplica el modo guardado (o el de `config.layout.variant`) sin escribir en localStorage. */
  applySaved(): void {
    this.applyMode(this.savedMode(), false);
  }

  toggle(): void {
    this.applyMode(this.isDark() ? 'light' : 'dark', true);
  }

  applyMode(mode: ThemeMode, persist: boolean): void {
    const body = this.document.body;
    const other = mode === 'dark' ? 'light' : 'dark';
    const skin = mode === 'dark' ? 'black' : 'white';

    this.renderer.removeClass(body, other);
    this.renderer.removeClass(body, other + '-sidebar');
    SKINS.forEach((s) => this.renderer.removeClass(body, 'theme-' + s));
    this.renderer.addClass(body, mode);
    this.renderer.addClass(body, mode + '-sidebar');
    this.renderer.addClass(body, 'theme-' + skin);
    this.isDark.set(mode === 'dark');

    if (persist) {
      try {
        localStorage.setItem('theme', mode);
        localStorage.setItem('menuOption', mode + '-sidebar');
        localStorage.setItem('choose_skin', 'theme-' + skin);
      } catch {
        // almacenamiento no disponible: el cambio aplica solo a esta sesion
      }
    }
  }

  private savedMode(): ThemeMode {
    let stored: string | null = null;
    try {
      stored = localStorage.getItem('theme');
    } catch {
      stored = null;
    }
    if (stored === 'dark' || stored === 'light') {
      return stored;
    }
    return this.configService.configData.layout.variant === 'dark' ? 'dark' : 'light';
  }
}
