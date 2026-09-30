import { Component, Input, forwardRef } from '@angular/core';
import { NG_VALUE_ACCESSOR, ControlValueAccessor } from '@angular/forms';

const ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
const MAX_SIZE_BYTES = 5 * 1024 * 1024;

/** Upload de imagen con preview/reemplazo/eliminación, reutilizable via
 * ControlValueAccessor. El valor del control es:
 * - null/undefined al inicio (sin cambios, se conserva `currentImageUrl`)
 * - un File cuando el usuario elige una imagen nueva
 * - null cuando el usuario hace click en "Quitar imagen"
 * `writeValue()` solo reacciona a un File real -- Angular siempre llama
 * writeValue() una vez al armar el control con su valor inicial, y
 * `FormControl` normaliza un valor inicial `undefined` a `null` (parametro
 * por defecto de su constructor), asi que null/undefined en writeValue()
 * nunca deben interpretarse como "el usuario quiso borrar la imagen" -- eso
 * solo lo decide `removeImage()`. El consumidor (ver `model-edit.component`)
 * distingue "nunca se tocó" de "se quitó" con `FormControl.dirty`, no con el
 * valor crudo del control.
 * La validación de tipo/tamaño es solo de UX -- el backend revalida siempre
 * (ver ADR-modulo-vehiculos-almacenamiento-imagenes). */
@Component({
  selector: 'app-image-upload',
  standalone: true,
  templateUrl: './image-upload.component.html',
  styleUrls: ['./image-upload.component.scss'],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => ImageUploadComponent),
      multi: true,
    },
  ],
})
export class ImageUploadComponent implements ControlValueAccessor {
  @Input() currentImageUrl: string | null = null;

  previewUrl: string | null = null;
  fileName: string | null = null;
  errorMessage = '';
  disabled = false;
  private removed = false;
  private failedUrl: string | null = null;

  private onChange: (value: File | null | undefined) => void = () => {};
  private onTouched: () => void = () => {};

  writeValue(value: File | null | undefined): void {
    if (value instanceof File) {
      this.setPreviewFromFile(value);
      this.removed = false;
    }
    // null/undefined llega siempre al menos una vez (valor inicial del
    // control) y nunca debe apagar la imagen existente -- ver comentario
    // de la clase. `removeImage()` es el unico lugar que pone `removed = true`.
  }

  registerOnChange(fn: (value: File | null | undefined) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled = isDisabled;
  }

  get displayUrl(): string | null {
    if (this.previewUrl) {
      return this.previewUrl;
    }
    if (!this.removed && this.currentImageUrl !== this.failedUrl) {
      return this.currentImageUrl;
    }
    return null;
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }
    this.errorMessage = '';

    if (!ALLOWED_TYPES.includes(file.type)) {
      this.errorMessage = 'Formato de imagen no permitido. Use JPG, PNG o WEBP.';
      input.value = '';
      return;
    }
    if (file.size > MAX_SIZE_BYTES) {
      this.errorMessage = 'La imagen no puede superar los 5 MB.';
      input.value = '';
      return;
    }

    this.removed = false;
    this.setPreviewFromFile(file);
    this.onChange(file);
    this.onTouched();
  }

  /** La imagen existente (remota) no cargo: se cae al placeholder. */
  onImageError(): void {
    if (!this.previewUrl) {
      this.failedUrl = this.currentImageUrl;
    }
  }

  removeImage(): void {
    this.previewUrl = null;
    this.fileName = null;
    this.removed = true;
    this.errorMessage = '';
    this.onChange(null);
    this.onTouched();
  }

  private setPreviewFromFile(file: File): void {
    this.fileName = file.name;
    const reader = new FileReader();
    reader.onload = () => {
      this.previewUrl = reader.result as string;
    };
    reader.readAsDataURL(file);
  }
}
