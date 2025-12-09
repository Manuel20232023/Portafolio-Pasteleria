from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.urls import path, include, reverse_lazy

app_name = 'tienda'

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    path('nosotros/', views.nosotros, name='nosotros'),

    # Productos
    path('productos/', views.productos_index, name='productos'),
    path('productos/categoria/<str:slug>/', views.productos_categoria, name='productos_categoria'),
    path('producto/<int:pk>/', views.producto_detalle, name='producto_detalle'),
    path('buscar/', views.buscar, name='buscar'),

    # Carrito
    path('carrito/', views.carrito_ver, name='carrito'),
    path('carrito/agregar/<int:pid>/', views.carrito_agregar, name='carrito_agregar'),
    path('carrito/eliminar/<int:pid>/', views.carrito_eliminar, name='carrito_eliminar'),
    path('carrito/vaciar/', views.carrito_vaciar, name='carrito_vaciar'),
    path('checkout/', views.checkout, name='checkout'),

    # Webpay
    path('webpay/iniciar/', views.webpay_iniciar, name='webpay_iniciar'),
    path('webpay/retorno/', views.webpay_retorno, name='webpay_retorno'),
    
    # Cuenta
    path('cuenta/login/', views.login_view, name='login'),
    path('cuenta/registro/', views.registro_view, name='registro'),
    path('cuenta/salir/', views.salir_view, name='salir'),

   # Restablecer contraseña
    path(
        'cuenta/restablecer/',
        auth_views.PasswordResetView.as_view(
            template_name='tienda/cuenta/restablecer.html',
            email_template_name='tienda/cuenta/restablecer_email.html',
            success_url=reverse_lazy('tienda:password_reset_done') 
        ),
        name='password_reset'
    ),
    path(
        'cuenta/restablecer/enviado/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='tienda/cuenta/restablecer_enviado.html'
        ),
        name='password_reset_done'
    ),
    path(
        'cuenta/restablecer/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='tienda/cuenta/restablecer_confirmar.html',
            success_url=reverse_lazy('tienda:password_reset_complete') 
        ),
        name='password_reset_confirm'
    ),
    path(
        'cuenta/restablecer/completado/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='tienda/cuenta/restablecer_completado.html'
        ),
        name='password_reset_complete'
    ),
]