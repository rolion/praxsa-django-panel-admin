"""Constantes del dashboard del panel (ver ADR-dashboard-taller-laminas-*).

Los umbrales de stock son PROVISIONALES: no hay dato en el codigo que los
respalde y deben confirmarse con el negocio antes de publicar."""
from decimal import Decimal

# Permiso Django de "Reporte Ventas Diaria": lo mismo que restringe las ventas cobradas
# en los reportes (ADR-reportes-utilidad-ventas-diarias-permisos). Admin y Caja.
PERMISO_VENTAS = 'product.view_proxy_pagos'

# Stock por sucursal + lamina + ancho, en metros disponibles para instalar.
STOCK_CRITICO_METROS = Decimal('10')
STOCK_BAJO_METROS = Decimal('30')

STOCK_OK = 'ok'
STOCK_BAJO = 'bajo'
STOCK_CRITICO = 'critico'

MESES_DEFECTO = 12
MESES_MAX = 12
COLA_MAX = 10
RECIENTES_MAX = 6
CONSUMO_MAX_SERIES = 6
ITEMS_MAX = 5
