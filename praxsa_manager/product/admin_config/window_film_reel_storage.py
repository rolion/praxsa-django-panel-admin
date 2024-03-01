from typing import Any
from django.contrib import admin
# from ..models import Window_Film_Reel_Storage
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
    
class WindowFilmReelStorage(admin.ModelAdmin):
    list_display = ['window_film_reel_id', 
                    'total_length']
    search_fields = ['window_film_reel_id__window_film__name', 
                    'total_length']
    list_per_page = 10

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        qs = super().get_queryset(request)
        result = qs.select_related('window_film_reel_id','window_film_reel_id__window_film')

        return  result