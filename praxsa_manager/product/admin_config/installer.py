
from django.contrib import admin
class Installer(admin.ModelAdmin):
    list_display = ['name', 'phonenumber', 'address']
    list_per_page = 10
    search_fields = ['name']