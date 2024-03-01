from django.contrib import admin

class CarBrand(admin.ModelAdmin):
    list_display = ['name']
    list_per_page = 10

    search_fields = ['name',]
