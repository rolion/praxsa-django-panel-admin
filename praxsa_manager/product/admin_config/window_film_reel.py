from typing import Any
from django.contrib import admin
from ..models import Window_Film_Reel_Storage
from ..models import Window_Film_Reel
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
    
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
    def save_model(self, request: Any, window_film_reel: Any, form: Any, change: Any) -> None:
        if change is False:
            reel = super().save_model(request, window_film_reel, form, change)
            total_length = 1*window_film_reel.length
            storage = Window_Film_Reel_Storage(window_film_reel_id=window_film_reel, total_length =  total_length)
            storage.save()
        else:
            original = Window_Film_Reel.objects.get(id = window_film_reel.id)
            storage = Window_Film_Reel_Storage.objects.get(window_film_reel_id = original.id)
            diff = window_film_reel.quantity - original.quantity
            if diff >= 1 :
                total_length = storage.total_length + diff*window_film_reel.lengt 
            else:
                total_length = window_film_reel.quantity*window_film_reel.length
            storage.total_length = total_length
            storage.save()
            super().save_model(request, window_film_reel, form, change)