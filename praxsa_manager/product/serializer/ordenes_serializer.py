"""Serializers del modulo Ordenes (Proformas y Notas de Trabajo) del panel
admin -- ver ADR-modulo-ordenes-proforma-nota-trabajo-api-y-calculo.

Regla de este modulo (REV-2026-09-27-modulo-almacen-01): los campos del modelo
no se redeclaran sin copiar sus validators/max_length; los que se ajustan
(required) se hacen via `extra_kwargs`, que conserva los validators del modelo.
"""
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from ..business.pricing import Pricing_Business, build_line_pricing
from ..business.proforma import Proforma_Business
from ..helper.pagos import Pagos_Helper
from ..helper.proforma import Proforma_Helper
from ..helper.user import User_Helper
from ..models import (
    Car_Model,
    Car_Part,
    Nota_trabajo,
    Nota_Venta,
    Proforma_Detail,
    Proforma_Header,
    Sucursal,
    Window_Film,
    registro_contable_regex,
)
from ..utils.exception.proforma import ProformaException


class ProformaLineSerializer(serializers.ModelSerializer):
    """Lectura de una linea de proforma (Proforma_Detail)."""

    car_part_name = serializers.SerializerMethodField()
    window_film_name = serializers.CharField(source='window_film.name', read_only=True)

    class Meta:
        model = Proforma_Detail
        fields = [
            'id', 'car_part', 'car_part_name', 'window_film', 'window_film_name',
            'width', 'length', 'quantity', 'window_film_price', 'installation_price', 'sub_total',
        ]

    def get_car_part_name(self, obj):
        return obj.car_part.name if obj.car_part_id else None


def _nota_trabajo_id(obj):
    nota = getattr(obj, 'nota_trabajo', None)
    return nota.id if nota is not None else None


class ProformaListSerializer(serializers.ModelSerializer):
    """Fila del listado de proformas (sin lineas)."""

    sales_type_label = serializers.CharField(source='get_sales_type_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    sucursal_name = serializers.SerializerMethodField()
    car_model_name = serializers.SerializerMethodField()
    car_brand_name = serializers.SerializerMethodField()
    total_a_pagar = serializers.SerializerMethodField()
    nota_trabajo_id = serializers.SerializerMethodField()

    class Meta:
        model = Proforma_Header
        fields = [
            'id', 'sales_type', 'sales_type_label', 'name', 'sucursal', 'sucursal_name',
            'car_model_name', 'car_brand_name', 'car_plate', 'total_price', 'discount',
            'total_a_pagar', 'proforma_created_on', 'status', 'status_label', 'is_close',
            'nota_trabajo_id',
        ]

    def get_sucursal_name(self, obj):
        return obj.sucursal.name if obj.sucursal_id else None

    def get_car_model_name(self, obj):
        return obj.car_model_id.name if obj.car_model_id_id else None

    def get_car_brand_name(self, obj):
        return obj.car_model_id.car_brand_id.name if obj.car_model_id_id else None

    def get_total_a_pagar(self, obj):
        return str(obj.total_price - obj.discount)

    def get_nota_trabajo_id(self, obj):
        return _nota_trabajo_id(obj)


class ProformaDetailSerializer(ProformaListSerializer):
    """Detalle de una proforma con sus lineas, para "Ver" y para precargar
    el formulario de edicion."""

    items = ProformaLineSerializer(many=True, read_only=True)
    nota_venta_id = serializers.SerializerMethodField()

    class Meta(ProformaListSerializer.Meta):
        fields = ProformaListSerializer.Meta.fields + [
            'email', 'ci_nit', 'phone_number', 'car_model_id', 'discount_reason', 'items', 'nota_venta_id',
        ]

    def get_nota_venta_id(self, obj):
        nota = getattr(obj, 'nota_trabajo', None)
        nota_venta = getattr(nota, 'nota_venta', None) if nota is not None else None
        return nota_venta.id if nota_venta is not None else None


class ProformaLineInputSerializer(serializers.Serializer):
    """Entrada de una linea de proforma. Solo los datos que elige la persona;
    `installation_price`, `window_film_price` y `sub_total` los calcula el
    servidor (no se aceptan)."""

    car_part = serializers.PrimaryKeyRelatedField(
        queryset=Car_Part.objects.filter(is_active=True), required=False, allow_null=True
    )
    window_film = serializers.PrimaryKeyRelatedField(queryset=Window_Film.objects.filter(is_active=True))
    width = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    length = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    quantity = serializers.IntegerField(required=False, allow_null=True, min_value=0)


class ProformaWriteSerializer(serializers.ModelSerializer):
    """Alta y edicion (PATCH) de una proforma. `total_price`, importes de
    linea, `created_by`, `status`, `is_close` e `is_delete` no se aceptan.
    Los campos del modelo conservan sus validators (email, telefono, CI/NIT,
    largos maximos)."""

    sucursal = serializers.PrimaryKeyRelatedField(
        queryset=Sucursal.objects.filter(enable_to_install_windows_film=True)
    )
    car_model_id = serializers.PrimaryKeyRelatedField(
        queryset=Car_Model.objects.filter(is_active=True), required=False, allow_null=True
    )
    items = ProformaLineInputSerializer(many=True, required=False)

    class Meta:
        model = Proforma_Header
        fields = [
            'sales_type', 'sucursal', 'name', 'email', 'ci_nit', 'phone_number',
            'car_plate', 'car_model_id', 'discount', 'discount_reason', 'items',
        ]
        # Igual que el formulario del Django Admin (que exige estos campos porque
        # no son blank=True), aunque el modelo tenga default/null.
        extra_kwargs = {
            'sales_type': {'required': True},
            'name': {'required': True},
            'email': {'required': True, 'allow_null': False},
            'ci_nit': {'required': True, 'allow_null': False},
            'phone_number': {'required': True},
            'discount_reason': {'allow_blank': True},
        }

    helper = Proforma_Helper()

    def _current(self, attrs, field, default=None):
        if field in attrs:
            return attrs[field]
        if self.instance is not None:
            return getattr(self.instance, field)
        return default

    def validate_sucursal(self, sucursal):
        if self.instance is not None:
            return sucursal
        user = self.context['request'].user
        if not User_Helper().get_sucursales_in_scope(user).filter(pk=sucursal.pk).exists():
            raise serializers.ValidationError('No tiene acceso a esa sucursal.')
        return sucursal

    def validate(self, attrs):
        instance = self.instance
        if instance is not None:
            if 'sales_type' in attrs and attrs['sales_type'] != instance.sales_type:
                raise serializers.ValidationError({'sales_type': 'El tipo de venta no se puede cambiar.'})
            if 'sucursal' in attrs and attrs['sucursal'].pk != instance.sucursal_id:
                raise serializers.ValidationError({'sucursal': 'La sucursal no se puede cambiar.'})

        sales_type = self._current(attrs, 'sales_type')
        sucursal = self._current(attrs, 'sucursal')
        car_model = self._current(attrs, 'car_model_id')
        car_plate = self._current(attrs, 'car_plate')

        if sales_type == self.helper.tipo_venta_instalacion:
            if car_model is None:
                raise serializers.ValidationError({'car_model_id': 'Tiene que seleccionar un modelo.'})
            if not (car_plate or '').strip():
                raise serializers.ValidationError({'car_plate': 'Tiene que agregar el número de placa.'})

        items = attrs.pop('items', None)
        if instance is None and not items:
            raise serializers.ValidationError({'items': ['Debe agregar al menos una línea.']})
        if items is not None and len(items) == 0:
            raise serializers.ValidationError({'items': ['Debe agregar al menos una línea.']})

        priced_items = None
        if items is not None:
            pricing_business = Pricing_Business()
            priced_items = []
            errors = []
            for index, item in enumerate(items, start=1):
                try:
                    pricing = build_line_pricing(
                        sales_type, car_model, sucursal, item, pricing_business=pricing_business
                    )
                except ProformaException as e:
                    errors.append(f'Línea {index}: {e.message}')
                    continue
                priced_items.append({
                    'car_part': item.get('car_part'),
                    'window_film': item['window_film'],
                    'width': item['width'],
                    'length': item['length'],
                    **pricing,
                })
            if errors:
                raise serializers.ValidationError({'items': errors})
            total = sum((p['sub_total'] for p in priced_items), Decimal('0'))
        else:
            total = instance.total_price

        discount = self._current(attrs, 'discount', Decimal('0'))
        discount_reason = self._current(attrs, 'discount_reason') or ''
        if discount > total * Decimal('0.5'):
            raise serializers.ValidationError(
                {'discount': 'El descuento no puede ser mayor que el 50% del precio total.'}
            )
        if discount > 0 and not discount_reason.strip():
            raise serializers.ValidationError(
                {'discount_reason': 'Debe agregar el motivo del descuento o quien aprueba este descuento.'}
            )

        attrs['_priced_items'] = priced_items
        return attrs

    @staticmethod
    def _replace_lines(proforma, priced_items):
        proforma.items.all().delete()
        Proforma_Detail.objects.bulk_create([
            Proforma_Detail(proforma_header=proforma, **priced) for priced in priced_items
        ])

    @transaction.atomic
    def create(self, validated_data):
        priced_items = validated_data.pop('_priced_items')
        proforma = Proforma_Header.objects.create(
            created_by=self.context['request'].user,
            total_price=Decimal('0'),
            **validated_data,
        )
        self._replace_lines(proforma, priced_items)
        Proforma_Business().recalculate_total_price(proforma)
        return proforma

    @transaction.atomic
    def update(self, instance, validated_data):
        priced_items = validated_data.pop('_priced_items', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if priced_items is not None:
            self._replace_lines(instance, priced_items)
            Proforma_Business().recalculate_total_price(instance)
        return instance

    def to_representation(self, instance):
        instance = Proforma_Header.objects.select_related(
            'sucursal', 'car_model_id', 'car_model_id__car_brand_id', 'nota_trabajo'
        ).prefetch_related('items__car_part', 'items__window_film').get(pk=instance.pk)
        return ProformaDetailSerializer(instance, context=self.context).data


class ReelCatalogSerializer(serializers.Serializer):
    """Fila del catalogo de bobinas (lamina + ancho con stock). Los importes y
    medidas viajan como strings con 2 decimales, igual que las lineas de proforma
    (un Response con Decimal crudo los codificaria como float, ver
    REV-2026-09-30-modulo-ordenes-proforma-nota-trabajo-02)."""

    window_film = serializers.IntegerField()
    window_film_name = serializers.CharField()
    width = serializers.DecimalField(max_digits=10, decimal_places=2)
    available_meters = serializers.DecimalField(max_digits=14, decimal_places=2)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class NotaTrabajoListSerializer(serializers.ModelSerializer):
    """Fila del listado de Notas de Trabajo."""

    proforma_id = serializers.IntegerField(read_only=True)
    sucursal_id = serializers.SerializerMethodField()
    sucursal_name = serializers.SerializerMethodField()
    car_model_name = serializers.SerializerMethodField()
    instalador_name = serializers.SerializerMethodField()
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    nota_venta = serializers.SerializerMethodField()

    class Meta:
        model = Nota_trabajo
        fields = [
            'id', 'proforma_id', 'name', 'car_model_name', 'car_plate', 'instaladar',
            'instalador_name', 'codigo_garantia', 'entrada_vehiculo', 'salida_vehiculo',
            'sucursal_id', 'sucursal_name', 'is_close', 'status', 'status_label', 'nota_venta',
        ]

    def get_sucursal_id(self, obj):
        return obj.proforma.sucursal_id if obj.proforma_id else None

    def get_sucursal_name(self, obj):
        proforma = obj.proforma
        return proforma.sucursal.name if proforma is not None and proforma.sucursal_id else None

    def get_car_model_name(self, obj):
        return obj.car_model.name if obj.car_model_id else None

    def get_instalador_name(self, obj):
        return obj.instaladar.name if obj.instaladar_id else None

    def get_nota_venta(self, obj):
        nota_venta = getattr(obj, 'nota_venta', None)
        if nota_venta is None:
            return None
        return {
            'id': nota_venta.id,
            'status': nota_venta.status,
            'status_label': nota_venta.get_status_display(),
            'total_price': str(nota_venta.total_price),
        }


class NotaTrabajoDetailSerializer(NotaTrabajoListSerializer):
    """Detalle de una Nota de Trabajo, con el resumen de laminas usadas y las
    lineas de la proforma de origen."""

    observaciones = serializers.CharField(read_only=True)
    responsable_name = serializers.SerializerMethodField()
    sales_type = serializers.SerializerMethodField()
    sales_type_label = serializers.SerializerMethodField()
    resumen = serializers.SerializerMethodField()
    proforma_items = serializers.SerializerMethodField()

    class Meta(NotaTrabajoListSerializer.Meta):
        fields = NotaTrabajoListSerializer.Meta.fields + [
            'observaciones', 'responsable_name', 'sales_type', 'sales_type_label',
            'resumen', 'proforma_items',
        ]

    def get_responsable_name(self, obj):
        return obj.responsable.username if obj.responsable_id else None

    def get_sales_type(self, obj):
        return obj.proforma.sales_type if obj.proforma_id else None

    def get_sales_type_label(self, obj):
        return obj.proforma.get_sales_type_display() if obj.proforma_id else None

    def get_resumen(self, obj):
        return [
            {'window_film_name': d.window_film.name if d.window_film_id else None,
             'width': d.width, 'length': d.length}
            for d in obj.detalle_trabajo.select_related('window_film')
        ]

    def get_proforma_items(self, obj):
        if not obj.proforma_id:
            return []
        items = obj.proforma.items.select_related('car_part', 'window_film')
        return ProformaLineSerializer(items, many=True).data


class NotaTrabajoUpdateSerializer(serializers.ModelSerializer):
    """PATCH operativo de una Nota de Trabajo: solo instalador, codigo de
    garantia, salida y observaciones. El resto (proforma, responsable,
    cliente, vehiculo, entrada) es de solo lectura."""

    class Meta:
        model = Nota_trabajo
        fields = ['instaladar', 'codigo_garantia', 'salida_vehiculo', 'observaciones']

    def validate_codigo_garantia(self, value):
        # unique + null=True: un '' se guardaria como valor y chocaria con el
        # siguiente '' -- se normaliza a NULL.
        return value or None

    def validate(self, attrs):
        instaladar = attrs.get('instaladar')
        proforma = self.instance.proforma if self.instance is not None else None
        cambia_instalador = self.instance is None or instaladar != self.instance.instaladar
        if instaladar is not None and cambia_instalador and not instaladar.is_active:
            raise serializers.ValidationError({'instaladar': 'El instalador está inactivo.'})
        if instaladar is not None and proforma is not None and proforma.sucursal_id:
            if not instaladar.sucursal.filter(pk=proforma.sucursal_id).exists():
                raise serializers.ValidationError(
                    {'instaladar': 'El instalador no pertenece a la sucursal de la proforma.'}
                )
        return attrs

    def to_representation(self, instance):
        return NotaTrabajoDetailSerializer(instance, context=self.context).data


class NotaVentaListSerializer(serializers.ModelSerializer):
    """Fila del listado de Notas de Venta (estado de cobro + estado del trabajo)."""

    status_label = serializers.CharField(source='get_status_display', read_only=True)
    nota_trabajo_id = serializers.IntegerField(read_only=True)
    proforma_id = serializers.SerializerMethodField()
    sucursal_id = serializers.SerializerMethodField()
    sucursal_name = serializers.SerializerMethodField()
    work_status = serializers.CharField(source='nota_trabajo.status', read_only=True)
    work_status_label = serializers.CharField(source='nota_trabajo.get_status_display', read_only=True)

    class Meta:
        model = Nota_Venta
        fields = [
            'id', 'nota_trabajo_id', 'proforma_id', 'name', 'ci_nit', 'total_price', 'created_on',
            'status', 'status_label', 'work_status', 'work_status_label', 'sucursal_id', 'sucursal_name',
        ]

    def _proforma(self, obj):
        return obj.nota_trabajo.proforma

    def get_proforma_id(self, obj):
        return obj.nota_trabajo.proforma_id

    def get_sucursal_id(self, obj):
        proforma = self._proforma(obj)
        return proforma.sucursal_id if proforma is not None else None

    def get_sucursal_name(self, obj):
        proforma = self._proforma(obj)
        return proforma.sucursal.name if proforma is not None and proforma.sucursal_id else None


class NotaVentaDetailSerializer(NotaVentaListSerializer):
    """Detalle de una Nota de Venta, con su pago (si existe)."""

    pago = serializers.SerializerMethodField()
    car_plate = serializers.SerializerMethodField()
    sales_type_label = serializers.SerializerMethodField()

    class Meta(NotaVentaListSerializer.Meta):
        fields = NotaVentaListSerializer.Meta.fields + ['pago', 'car_plate', 'sales_type_label']

    def get_pago(self, obj):
        pago_obj = getattr(obj, 'pago', None)
        if pago_obj is None:
            return None
        return {
            'id': pago_obj.id,
            'monto': str(pago_obj.monto),
            'tipo_pago': pago_obj.tipo_pago,
            'tipo_pago_label': pago_obj.get_tipo_pago_display(),
            'registro_contable': pago_obj.registro_contable,
            'created_on': pago_obj.created_on,
            'cerrado': pago_obj.cerrado,
        }

    def get_car_plate(self, obj):
        return obj.nota_trabajo.car_plate

    def get_sales_type_label(self, obj):
        proforma = self._proforma(obj)
        return proforma.get_sales_type_display() if proforma is not None else None


class PagoInputSerializer(serializers.Serializer):
    """Datos que envia el cliente al registrar un pago. El monto NO se acepta:
    lo fija el servidor (total de la nota de venta)."""

    tipo_pago = serializers.ChoiceField(choices=Pagos_Helper().types, required=False, default=Pagos_Helper().default_type)
    registro_contable = serializers.CharField(
        max_length=7, required=False, allow_blank=True, allow_null=True, validators=[registro_contable_regex]
    )
