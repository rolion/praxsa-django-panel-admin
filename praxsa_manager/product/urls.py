from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views
from rest_framework.authtoken import views as rf_token
from .custom_views.auth_token import CustomAuthToken, PanelAdminAuthToken
from .custom_views.invoice import InvoiceView, ListUserInvoice
from .custom_views.bobina import BobinaView
from .custom_views.user_admin import (
    GroupDetailView,
    GroupListCreateView,
    PermissionListView,
    SucursalDetailView,
    SucursalListCreateView,
    UserDetailView,
    UserListCreateView,
    UserSetPasswordView,
    UserToggleActiveView,
)
from .custom_views.vehicle_admin import (
    CarBrandDetailView,
    CarBrandListCreateView,
    CarBrandToggleActiveView,
    CarModelDetailView,
    CarModelItemDetailView,
    CarModelItemsView,
    CarModelListCreateView,
    CarModelToggleActiveView,
    CarPartDetailView,
    CarPartListCreateView,
    CarPartToggleActiveView,
)
from .custom_views.almacen_admin import (
    InventarioListView,
    InventarioToggleActiveView,
    InventarioUpdateView,
    WindowFilmDetailView,
    WindowFilmListCreateView,
    WindowFilmReelDetailView,
    WindowFilmReelListCreateView,
    WindowFilmReelToggleActiveView,
    WindowFilmToggleActiveView,
)
from .custom_views.ordenes_admin import (
    NotaTrabajoAnularView,
    NotaTrabajoCorregirView,
    NotaTrabajoDetailView,
    NotaTrabajoListView,
    NotaTrabajoTerminarView,
    NotaVentaAnularPagoView,
    NotaVentaAnularView,
    NotaVentaDetailView,
    NotaVentaListView,
    NotaVentaPagoView,
    OrdenesBobinasView,
    OrdenesInstaladoresView,
    OrdenesSucursalesView,
    ProformaAnularView,
    ProformaDetailView,
    ProformaGenerateNotaView,
    ProformaListCreateView,
    ProformaPdfView,
)
app_name = 'product'
urlpatterns = [
    path('get_car_part_info/<int:car_model_id>/<int:sucursal_id>', views.get_car_part_info, name= 'get_car_part_info'),
    path('get_proforma_car_part_info/<int:proforma_id>', views.get_proforma_car_part_info, name= 'get_car_part_info'),
    # 
    path('calculator_info', views.get_calculator_info, name='get_calculator_info'),
    # path('get_item_film_inventory/<int:sucursal_id>/<int:car_model_id>/<int:item_id>', views.get_item_film_inventory, name="get_item_film_inventory"),
    path('model_parts/<int:model_id>', views.get_model_parts,name = 'get_model_parts'),
    path('get_inventory/<int:sucursal_id>/<int:lamina_id>/<str:width>', views.get_inventory, name='get_inventory'),
    path('create_client', views.create_client, name='create_client'),
    path('api-token-auth/', CustomAuthToken.as_view()),
    path('api-panel-admin-token-auth/', PanelAdminAuthToken.as_view()),
    path('invoice', InvoiceView.as_view()),
    path('invoice/<int:pk>/', InvoiceView.as_view()),
    path('invoice/all', ListUserInvoice.as_view()),
    path('bobina/<int:pk>', views.get_bobina, name='get_bobina'),
    path('layer/<int:layer_id>', views.get_layer_info, name='get_layer_info'),
    # Modulo de Usuarios, Perfiles, Grupos, Roles y Sucursales (panel_admin/)
    # (el login del panel es PanelAdminAuthToken, arriba -- ver TASK-login-panel-admin-backend)
    path('users', UserListCreateView.as_view()),
    path('users/<int:pk>/', UserDetailView.as_view()),
    path('users/<int:pk>/set-password/', UserSetPasswordView.as_view()),
    path('users/<int:pk>/toggle-active/', UserToggleActiveView.as_view()),
    path('groups', GroupListCreateView.as_view()),
    path('groups/<int:pk>/', GroupDetailView.as_view()),
    path('permissions', PermissionListView.as_view()),
    path('sucursales', SucursalListCreateView.as_view()),
    path('sucursales/<int:pk>/', SucursalDetailView.as_view()),
    # Modulo de Vehiculos: Marcas, Modelos, Items (panel_admin/)
    path('vehicles/brands', CarBrandListCreateView.as_view()),
    path('vehicles/brands/<int:pk>/', CarBrandDetailView.as_view()),
    path('vehicles/brands/<int:pk>/toggle-active/', CarBrandToggleActiveView.as_view()),
    path('vehicles/models', CarModelListCreateView.as_view()),
    path('vehicles/models/<int:pk>/', CarModelDetailView.as_view()),
    path('vehicles/models/<int:pk>/toggle-active/', CarModelToggleActiveView.as_view()),
    path('vehicles/models/<int:model_id>/items/', CarModelItemsView.as_view()),
    path('vehicles/models/<int:model_id>/items/<int:pk>/', CarModelItemDetailView.as_view()),
    path('vehicles/parts', CarPartListCreateView.as_view()),
    path('vehicles/parts/<int:pk>/', CarPartDetailView.as_view()),
    path('vehicles/parts/<int:pk>/toggle-active/', CarPartToggleActiveView.as_view()),
    # Modulo Almacen: Laminas, Bobinas, Inventario (panel_admin/)
    path('almacen/laminas', WindowFilmListCreateView.as_view()),
    path('almacen/laminas/<int:pk>/', WindowFilmDetailView.as_view()),
    path('almacen/laminas/<int:pk>/toggle-active/', WindowFilmToggleActiveView.as_view()),
    path('almacen/bobinas', WindowFilmReelListCreateView.as_view()),
    path('almacen/bobinas/<int:pk>/', WindowFilmReelDetailView.as_view()),
    path('almacen/bobinas/<int:pk>/toggle-active/', WindowFilmReelToggleActiveView.as_view()),
    path('almacen/inventario', InventarioListView.as_view()),
    path('almacen/inventario/<int:pk>/', InventarioUpdateView.as_view()),
    path('almacen/inventario/<int:pk>/toggle-active/', InventarioToggleActiveView.as_view()),
    # Modulo Ordenes: Proformas y Notas de Trabajo (panel_admin/)
    path('ordenes/proformas', ProformaListCreateView.as_view()),
    path('ordenes/proformas/<int:pk>/', ProformaDetailView.as_view()),
    path('ordenes/proformas/<int:pk>/generar-nota-trabajo/', ProformaGenerateNotaView.as_view()),
    path('ordenes/proformas/<int:pk>/anular/', ProformaAnularView.as_view()),
    path('ordenes/proformas/<int:pk>/pdf/', ProformaPdfView.as_view()),
    path('ordenes/notas-trabajo', NotaTrabajoListView.as_view()),
    path('ordenes/notas-trabajo/<int:pk>/', NotaTrabajoDetailView.as_view()),
    path('ordenes/notas-trabajo/<int:pk>/terminar/', NotaTrabajoTerminarView.as_view()),
    path('ordenes/notas-trabajo/<int:pk>/corregir/', NotaTrabajoCorregirView.as_view()),
    path('ordenes/notas-trabajo/<int:pk>/anular/', NotaTrabajoAnularView.as_view()),
    path('ordenes/notas-venta', NotaVentaListView.as_view()),
    path('ordenes/notas-venta/<int:pk>/', NotaVentaDetailView.as_view()),
    path('ordenes/notas-venta/<int:pk>/pago/', NotaVentaPagoView.as_view()),
    path('ordenes/notas-venta/<int:pk>/anular-pago/', NotaVentaAnularPagoView.as_view()),
    path('ordenes/notas-venta/<int:pk>/anular/', NotaVentaAnularView.as_view()),
    path('ordenes/catalogo/sucursales', OrdenesSucursalesView.as_view()),
    path('ordenes/catalogo/bobinas', OrdenesBobinasView.as_view()),
    path('ordenes/catalogo/instaladores', OrdenesInstaladoresView.as_view()),
]
urlpatterns = format_suffix_patterns(urlpatterns)