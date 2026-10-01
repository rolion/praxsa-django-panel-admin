import { DecimalPipe } from '@angular/common';
import { Component, input, output } from '@angular/core';
import { AppCarModelPart } from '../vehicles.model';

/** Tarjeta de una parte (Car_Model_Part) asociada a un Modelo. Solo
 * presenta los datos y emite `edit`/`remove`; los modales y la confirmación
 * viven en ModelViewComponent. Ver DDR-vehiculo-detalle-partes-ui-vista-
 * detalle-modelo. */
@Component({
  selector: 'app-model-item-card',
  standalone: true,
  imports: [DecimalPipe],
  templateUrl: './model-item-card.component.html',
})
export class ModelItemCardComponent {
  item = input.required<AppCarModelPart>();
  edit = output<AppCarModelPart>();
  remove = output<AppCarModelPart>();
}
