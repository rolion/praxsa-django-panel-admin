from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from ..models import Profile, Sucursal


class UserAdminSerializer(serializers.ModelSerializer):
    """Lectura y edicion (sin password) de un usuario administrado desde
    panel_admin/. La creacion (con password) usa UserCreateSerializer."""

    phone_number = serializers.CharField(
        source='profile.phone_number', required=False, allow_null=True, allow_blank=True
    )
    groups = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), many=True, required=False
    )
    sucursales = serializers.PrimaryKeyRelatedField(
        queryset=Sucursal.objects.all(), many=True, required=False, source='sucursal_set'
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_active', 'is_staff', 'phone_number', 'groups', 'sucursales',
        ]
        read_only_fields = ['id', 'username', 'is_staff']

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        groups = validated_data.pop('groups', None)
        sucursales = validated_data.pop('sucursal_set', None)
        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            if profile_data is not None:
                Profile.objects.update_or_create(
                    user=instance, defaults=profile_data
                )
            if groups is not None:
                instance.groups.set(groups)
            if sucursales is not None:
                instance.sucursal_set.set(sucursales)
        return instance


class UserCreateSerializer(serializers.Serializer):
    """Crea User + Profile + grupos + sucursales de forma atomica, para el
    paso de confirmacion del wizard de 4 pasos (un solo POST, ver ADR
    api-autenticacion-admin). Los usuarios creados aqui quedan is_staff=True,
    ya que este modulo administra cuentas de acceso al panel/admin, no
    clientes finales (esos siguen creandose via create_client)."""

    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    is_active = serializers.BooleanField(default=True)
    first_name = serializers.CharField(required=False, allow_blank=True, default='')
    last_name = serializers.CharField(required=False, allow_blank=True, default='')
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    phone_number = serializers.RegexField(
        regex=r'(\+)*\d{7,11}', required=False, allow_blank=True, allow_null=True, default=None
    )
    sucursales = serializers.PrimaryKeyRelatedField(
        queryset=Sucursal.objects.all(), many=True, required=False, default=list
    )
    groups = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), many=True, required=False, default=list
    )

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('El nombre de usuario ya existe.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': ['Las contraseñas no coinciden.']})
        try:
            validate_password(attrs['password'])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': list(exc.messages)})
        return attrs

    def create(self, validated_data):
        sucursales = validated_data.pop('sucursales', [])
        groups = validated_data.pop('groups', [])
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        phone_number = validated_data.pop('phone_number', None)

        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['username'],
                password=password,
                email=validated_data.get('email', ''),
                first_name=validated_data.get('first_name', ''),
                last_name=validated_data.get('last_name', ''),
                is_active=validated_data.get('is_active', True),
                is_staff=True,
            )
            Profile.objects.create(user=user, phone_number=phone_number)
            if groups:
                user.groups.set(groups)
            for sucursal in sucursales:
                sucursal.empleado.add(user)
        return user
