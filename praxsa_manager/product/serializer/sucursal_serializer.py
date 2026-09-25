from rest_framework import serializers

from ..models import Sucursal


class SucursalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sucursal
        fields = ['id', 'name', 'address', 'phone_number', 'enable_to_install_windows_film']
