from rest_framework import serializers
from django.contrib.auth.models import User
from ..models import Client
from rest_framework.validators import UniqueValidator

class ClientSerializer(serializers.Serializer):
    email = serializers.EmailField(required= True, max_length=100, 
                                     validators=[UniqueValidator(queryset = User.objects.all(), 
                                                                 message ='email ya existe')])
    password = serializers.CharField(required= True)
    name = serializers.CharField(required= True)
    lastname = serializers.CharField(required= True)
    phone_number = serializers.RegexField(regex='(\+)*\d{7,11}', required= True)
    ci_nit = serializers.CharField(required= False, allow_blank = True)
    
    def create(self, validated_data):
        if self.is_valid():
            newUser = User.objects.create_user(
                username=validated_data['email'], 
                password=validated_data['password'],
                email=validated_data['email'],
                first_name= validated_data['name'],
                last_name= validated_data['lastname'])
            newUser.save()
            client = Client(name= validated_data['name'], 
                            last_name= validated_data['lastname'],
                            phone_number= validated_data['phone_number'],
                            ci_nit= validated_data['ci_nit'],
                            user_id = newUser)
            client.save()
            validated_data['password']= ' '
            return validated_data
        return self.errors
    
    def validate_ci_nit(self, ci_nit):
        if ci_nit == '':
            return ci_nit
        if not ci_nit.isnumeric():
            raise serializers.ValidationError("insert a valid ci/nit")
        return ci_nit