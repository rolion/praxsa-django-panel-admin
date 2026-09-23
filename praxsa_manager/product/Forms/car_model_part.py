from decimal import Decimal, ROUND_HALF_UP
from django import forms
from django.forms import ModelForm
from ..models import Proforma_Detail, Car_Model_Part
from django.core.exceptions import ValidationError
from ..helper.proforma import Proforma_Helper
from ..helper.inventory import Inventory_helper
from ..business.inventario import Inventario_Business
from ..business.pricing import Pricing_Business, calculate_subtotal_venta_instalacion

class CarItemField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.description

class CarModelPartForm(ModelForm):

    disponibilidad = forms.IntegerField(required=False, initial = 0, disabled=True)
    proforma_helper = Proforma_Helper()
    inv_helper = Inventory_helper()
    inv_bussiness = Inventario_Business()
    pricing_business = Pricing_Business()

    def is_proforma_approved(self, proforma):
        return proforma.sales_status == self.proforma_helper.apr
    
    def is_proforma_installed(self, proforma):
        return proforma.sales_status == self.proforma_helper.inst
    
    def is_inventory_valid(self, sucursal, lamina, mtr_to_install, width):
        return self.inv_helper.get_bobina_by_sucursal_lamina_width(sucursal_id=sucursal, lamina_id=lamina,width=width, length_to_sell= mtr_to_install )
    
    def clean_sub_total(self):
        cleaned_data = super().clean()
        cc_sub_total = cleaned_data.get("sub_total")
        if not cc_sub_total.compare(0) == 1:
            raise ValidationError("sub total invalido, no puede ser 0")
        return cc_sub_total
        
    def clean_length(self):
        cleaned_data = super().clean()
        cc_length = cleaned_data.get("length")
        if cc_length > 0:
            return cc_length
        else:
            raise ValidationError('tiene que ser mayor a 0')
    
    def item_width_lte_film_width(self, item, model, width):
        query = Car_Model_Part.objects.select_related('car_part_id', 'car_model_id').filter(car_model_id = model, car_part_id = item, width__lte = width)
        return query.exists()

    
    def clean(self):
        cleaned_data = super().clean()
        cc_width = cleaned_data.get('width')
        cc_car_part_id = cleaned_data.get('car_part')
        cc_quantity = cleaned_data.get('quantity')
        cc_installation_price = cleaned_data.get('installation_price')
        cc_length = cleaned_data.get('length')
        sale_header = cleaned_data.get("proforma_header")
        cc_window_film = cleaned_data.get("window_film")

        if cc_length is None:
            self.add_error('length','este campo es requerido')
            return

        if sale_header is not None and sale_header.sales_type == self.proforma_helper.tipo_venta_instalacion:
            if cc_width is None or self.item_width_lte_film_width(cc_car_part_id, sale_header.car_model_id, cc_width) == False:
                self.add_error('window_film','el ancho de la bobina es menor que el ancho del item')
            if cc_quantity is None or cc_quantity < 1:
                self.add_error('quantity','campo requerido')
            if cc_installation_price is None or cc_installation_price < 1:
                self.add_error('installation_price','campo requerido')

            # available_reel = self.inv_bussiness.available_window_film_reel_in_inventory_to_sell(width=cc_width,
            #                                                                                     windows_film=cc_window_film,
            #                                                                                     sucursal=sale_header.sucursal,
            #                                                                                     total_length_to_sell=cc_length * cc_quantity)

            # El precio nunca se confía del form (calculado client-side por sales_event.js):
            # se recalcula acá con los precios reales y se sobrescribe siempre. Ver ADR-006.
            # Solo se intenta si quantity/width ya son válidos — sin ellos no hay subtotal que
            # calcular, y los errores 'campo requerido' de arriba ya bastan para invalidar el form.
            if cc_quantity is not None and cc_width is not None:
                car_model_part = Car_Model_Part.objects.filter(
                    car_model_id=sale_header.car_model_id, car_part_id=cc_car_part_id
                ).first()
                if car_model_part is None:
                    self.add_error('car_part', 'No existe información de precio de instalación para este ítem en el modelo seleccionado.')
                elif cc_window_film is None:
                    self.add_error('window_film', 'Tiene que seleccionar una lámina.')
                else:
                    unit_price = self.pricing_business.resolve_unit_price(
                        sucursal_id=getattr(sale_header, 'sucursal_id', None),
                        lamina_id=cc_window_film.id,
                        width=cc_width,
                    )
                    if unit_price is None:
                        self.add_error('window_film', 'No hay precio disponible para la lámina/ancho solicitado en esa sucursal.')
                    else:
                        cleaned_data['installation_price'] = car_model_part.installation_price
                        cleaned_data['window_film_price'] = unit_price
                        # La multiplicación de Decimals conserva exponentes (p. ej. 1.00 * 120.00 =
                        # 120.0000), lo que hace fallar el DecimalValidator(decimal_places=2) que
                        # ModelForm._post_clean() corre sobre el modelo — se redondea explícito acá.
                        cleaned_data['sub_total'] = calculate_subtotal_venta_instalacion(
                            length=cc_length,
                            quantity=cc_quantity,
                            unit_price=unit_price,
                            installation_price=car_model_part.installation_price,
                        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        if sale_header is not None and sale_header.sales_type == self.proforma_helper.tipo_venta_metro_lineal:
        #     if cc_car_part_id is not None:
        #         self.add_error('car_part_id','este campo no es requerido')
            if cc_quantity is not None and cc_quantity > 0:
                self.add_error('quantity','campo no requerido')
            if cc_installation_price is not None and cc_installation_price.compare(0) == 1:
                self.add_error('installation_price','campo no requerido')
        
        total_length_to_sell=cc_length * (cc_quantity if cc_quantity is not None and cc_quantity > 0 else 1)
        # available_reel = self.inv_bussiness.available_window_film_reel_in_inventory_to_sell(width=cc_width, 
        #                                                                                         windows_film=cc_window_film, 
        #                                                                                         sucursal=sale_header.sucursal, 
        #                                                                                         total_length_to_sell=total_length_to_sell)
        # if available_reel.exists() is False:
        #     self.add_error('window_film','no hay disponibilidad de lamina')

        return cleaned_data

    def update_inventory(self, sucursal, bobina, length_to_reduce):
        self.inv_helper.update_inventory(sucursal_id= sucursal, bobina= bobina, length_to_reduce=length_to_reduce)

    class Meta:
        model = Proforma_Detail
        fields = "__all__"
        