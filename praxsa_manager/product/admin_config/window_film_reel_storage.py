from typing import Any
from django.contrib import admin
from ..models import Window_Film_Reel_Storage
    
class WindowFilmReelStorage(admin.ModelAdmin):
    list_display = ['window_film_reel_id', 
                    'total_length']
    list_per_page = 10