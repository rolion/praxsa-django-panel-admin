from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from ..models import Client


class ClientRegisterSerializer(serializers.Serializer):
    """Registro de cliente final desde panel_admin/ (ADR-pricing-calculator-screen-
    registro-y-api-cliente). A diferencia de `ClientSerializer` (create_client, que usa
    proforma/ y no se toca): guarda la placa en la cuenta, acepta un `username` propio
    (por defecto el correo) y valida la contraseña con los validadores de Django.

    Solo declara campos de perfil: cualquier otro (p. ej. `is_staff`, `groups`) se ignora,
    un cliente nunca recibe privilegios de administracion."""

    name = serializers.CharField(max_length=150)
    lastname = serializers.CharField(max_length=150)
    email = serializers.EmailField(
        max_length=100,
        validators=[UniqueValidator(queryset=User.objects.all(), lookup='iexact', message='email ya existe')],
    )
    phone_number = serializers.RegexField(regex=r'^(\+)?\d{7,11}$', max_length=12)
    car_plate = serializers.CharField(max_length=10)
    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate_username(self, value):
        value = value.strip()
        if not value:
            return value
        if any(ch.isspace() for ch in value):
            raise serializers.ValidationError('El usuario no puede contener espacios.')
        return value

    def validate(self, data):
        username = data.get('username') or data['email']
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError({'username': 'usuario ya existe'})
        data['username'] = username

        candidate = User(username=username, email=data['email'], first_name=data['name'], last_name=data['lastname'])
        try:
            validate_password(data['password'], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': list(exc.messages)})
        return data

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data['email'],
            first_name=validated_data['name'],
            last_name=validated_data['lastname'],
        )
        Client.objects.create(
            name=validated_data['name'],
            last_name=validated_data['lastname'],
            phone_number=validated_data['phone_number'],
            ci_nit='',
            car_plate=validated_data['car_plate'],
            user_id=user,
        )
        return user
