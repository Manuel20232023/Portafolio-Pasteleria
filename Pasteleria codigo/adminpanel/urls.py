from django.urls import path
from . import views

app_name = 'adminpanel'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('reportes/', views.reportes, name='reportes'),
    path('reportes/pdf/', views.descargar_reporte, name='descargar_reporte'),
    path('reportes/excel/', views.descargar_reporte_excel, name='descargar_reporte_excel'),
    path('pedidos/', views.pedidos_view, name='pedidos'),
    path('clientes/', views.clientes, name='clientes'),
    path("productos/", views.productos, name="productos"),
    path('promociones/', views.promociones, name='promociones'),
    path('productos/eliminar/<int:pk>/', views.eliminar_producto, name='eliminar_producto'),
    path('productos/editar/<int:pk>/', views.editar_producto, name='editar_producto'),
    path('promociones/editar/<int:pk>/', views.editar_promocion, name='editar_promocion'),
    path('promociones/eliminar/<int:pk>/', views.eliminar_promocion, name='eliminar_promocion'),
]