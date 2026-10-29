from django.urls import path

from . import views

app_name = 'store'

urlpatterns = [
    path('__development-version__/', views.development_version, name='development_version'),
    path('', views.catalog, name='catalog'),
    path('cuenta/iniciar-sesion/', views.login_view, name='login'),
    path('cuenta/registro/', views.register_customer, name='register_customer'),
    path('cuenta/registro-tejedora/', views.register_craftswoman, name='register_craftswoman'),
    path('cuenta/salir/', views.logout_view, name='logout'),
    path('mi-cuenta/', views.customer_dashboard, name='customer_dashboard'),
    path('mi-cuenta/configuracion/', views.account_settings, name='account_settings'),
    path('panel-tejedora/', views.craftswoman_dashboard, name='craftswoman_dashboard'),
    path('panel-tejedora/pedido/<int:order_id>/aceptar/', views.accept_order, name='accept_order'),
    path('panel-tejedora/pedido/<int:order_id>/estado/', views.update_order_status, name='update_order_status'),
    path('panel-tejedora/diseno/<int:design_id>/estado/', views.update_design_status, name='update_design_status'),
    path('producto/<int:product_id>/', views.product_detail, name='product_detail'),
    path('disena-tu-manta/', views.custom_designer, name='custom_designer'),
    path('carrito/', views.cart, name='cart'),
    path('carrito/agregar/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('carrito/actualizar/<int:product_id>/', views.update_cart, name='update_cart'),
    path('carrito/eliminar/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('finalizar-pedido/', views.checkout, name='checkout'),
    path('pedido-confirmado/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
]
