from typing import Any
from django.contrib import admin
# from ..models import Window_Film_Reel_Storage
from ..models import Window_Film_Reel, inventario
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.contrib import messages
from django.utils.translation import ngettext
    
class WindowFilmReel(admin.ModelAdmin):
    list_display = ['window_film', 
                    'width',
                    'length',
                    'price',]
    search_fields = ['window_film__name', 
                    'width',
                    'length',
                    'price',]
    list_per_page = 10
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request)
        result = qs.select_related('window_film')
        return  result
    
    def delete_model(self, request, obj):
        inventory_list = inventario.objects.select_related('bobina').filter(bobina__id = obj.id)
        if len(inventory_list) > 0:
            messages.set_level(request, messages.ERROR) 
            messages.error(
                request=request,
                message=str('la bobina seleccionada esta asignada a uno o muchos inventarios, no se puede eliminar')
            )
        else:
            super().delete_model(request, obj)  
    
    
    def delete_queryset(self, request, queryset) -> None:
        ids = queryset.values_list('id', flat=True)
        inventory_list = inventario.objects.select_related('bobina').filter(bobina__id__in = ids)
        if len(inventory_list) > 0:
            messages.set_level(request, messages.ERROR) 
            messages.error(
                request=request,
                message=str('la(s) bobina(s) seleccionada(s) esta asignada a uno o muchos inventarios, no se puede eliminar')
            )
        else:
            super().delete_queryset(request, queryset)
            
            