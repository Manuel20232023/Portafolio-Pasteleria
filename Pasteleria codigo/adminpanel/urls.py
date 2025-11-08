from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('reportes/', views.reportes, name='reportes'),
    path('reportes/pdf/', views.descargar_reporte, name='descargar_reporte'),
    path('reportes/excel/', views.descargar_reporte_excel, name='descargar_reporte_excel'),
    path('pedidos/', views.pedidos_view, name='pedidos'),
    path('clientes/', views.clientes, name='clientes'),
    path("productos/", views.productos, name="productos"),
    path('promociones/', views.promociones, name='promociones'),
]