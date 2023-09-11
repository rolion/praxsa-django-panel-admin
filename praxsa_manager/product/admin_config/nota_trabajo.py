from typing import Any
from django import forms
from django.contrib import admin
from ..Forms.nota_trabajo import NotaTrabajoForm
# class ProformaDetailInLine(admin.TabularInline):
class NotaTrabajoAdmin(admin.ModelAdmin):
    # list_display = [
    #             'id',
    #             'sales_status',
    #             'sales_type',
    #             'codigo_garantia',
    #             'name', 
    #             'car_model_id',
    #             'total_price',
    #             'proforma_created_on'
    #             ]
    # inlines = [
    #     ProformaDetailInLine,
    # ]
    # readonly_fields = ['sales_status']
    form = NotaTrabajoForm
    list_per_page = 10
    