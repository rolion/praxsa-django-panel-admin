from django.contrib import admin
    
class WindowFilm(admin.ModelAdmin):
    list_display = ['name', 
                    'description']
    list_per_page = 10