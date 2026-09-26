import { TestBed } from '@angular/core/testing';
import { ImageUploadComponent } from './image-upload.component';

function fileInputEvent(file: File): Event {
  const input = document.createElement('input');
  input.type = 'file';
  Object.defineProperty(input, 'files', { value: [file] });
  return { target: input } as unknown as Event;
}

describe('ImageUploadComponent', () => {
  let component: ImageUploadComponent;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [ImageUploadComponent] });
    const fixture = TestBed.createComponent(ImageUploadComponent);
    component = fixture.componentInstance;
  });

  it('shows the current image url when no new file was chosen', () => {
    component.currentImageUrl = 'http://localhost/media/car_models/foo.jpg';
    component.writeValue(undefined);

    expect(component.displayUrl).toBe('http://localhost/media/car_models/foo.jpg');
  });

  it('rejects a file with a disallowed type and does not call onChange', () => {
    let changedValue: unknown = 'untouched';
    component.registerOnChange((value) => (changedValue = value));
    const badFile = new File(['x'], 'nota.txt', { type: 'text/plain' });

    component.onFileSelected(fileInputEvent(badFile));

    expect(component.errorMessage).toContain('JPG, PNG o WEBP');
    expect(changedValue).toBe('untouched');
  });

  it('rejects a file bigger than 5MB and does not call onChange', () => {
    let changedValue: unknown = 'untouched';
    component.registerOnChange((value) => (changedValue = value));
    const bigContent = new Uint8Array(6 * 1024 * 1024);
    const bigFile = new File([bigContent], 'grande.jpg', { type: 'image/jpeg' });

    component.onFileSelected(fileInputEvent(bigFile));

    expect(component.errorMessage).toContain('5 MB');
    expect(changedValue).toBe('untouched');
  });

  it('accepts a valid image and reports it via onChange', () => {
    let changedValue: unknown = 'untouched';
    component.registerOnChange((value) => (changedValue = value));
    const goodFile = new File(['x'], 'vehiculo.jpg', { type: 'image/jpeg' });

    component.onFileSelected(fileInputEvent(goodFile));

    expect(component.errorMessage).toBe('');
    expect(changedValue).toBe(goodFile);
    expect(component.fileName).toBe('vehiculo.jpg');
  });

  it('removeImage() clears the preview and reports null via onChange', () => {
    component.currentImageUrl = 'http://localhost/media/car_models/foo.jpg';
    let changedValue: unknown = 'untouched';
    component.registerOnChange((value) => (changedValue = value));

    component.removeImage();

    expect(component.displayUrl).toBeNull();
    expect(changedValue).toBeNull();
  });
});
