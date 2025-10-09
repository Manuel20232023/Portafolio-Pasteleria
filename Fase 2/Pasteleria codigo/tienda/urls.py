from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'tienda'

urlpatterns = [
    path('', views.home, name='home'),
    path('nosotros/', views.nosotros, name='nosotros'),

    # Productos
    path('productos/', views.productos_index, name='productos'),
    path('productos/<str:slug>/', views.productos_categoria, name='productos_categoria'),
    # Búsqueda
    path('buscar/', views.buscar, name='buscar'),

    # Cuenta
    path('cuenta/login/', views.login_view, name='login'),
    path('cuenta/registro/', views.registro_view, name='registro'),
    path('cuenta/salir/', views.salir_view, name='salir'),

    # Restablecer contraseña (usa vistas de Django)
    path('cuenta/restablecer/', 
         auth_views.PasswordResetView.as_view(template_name='tienda/cuenta/restablecer.html'),
         name='password_reset'),
    path('cuenta/restablecer/enviado/', 
         auth_views.PasswordResetDoneView.as_view(template_name='tienda/cuenta/restablecer_enviado.html'),
         name='password_reset_done'),
    path('cuenta/restablecer/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='tienda/cuenta/restablecer_confirmar.html'),
         name='password_reset_confirm'),
    path('cuenta/restablecer/completado/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='tienda/cuenta/restablecer_completado.html'),
         name='password_reset_complete'),

    # Carrito
    path('carrito/', views.carrito_ver, name='carrito'),
    path('carrito/agregar/<slug:pid>/', views.carrito_agregar, name='carrito_agregar'),
    path('carrito/eliminar/<slug:pid>/', views.carrito_eliminar, name='carrito_eliminar'),
    path('carrito/vaciar/', views.carrito_vaciar, name='carrito_vaciar'),
    path('checkout/', views.checkout, name='checkout'),
]

path('cuenta/salir/', views.salir_view, name='salir'),
