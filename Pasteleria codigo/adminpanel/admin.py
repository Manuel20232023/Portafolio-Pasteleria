from django.contrib import admin
from .models import Producto, Promocion # Importamos ambos

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio', 'stock', 'destacado')
    list_filter = ('categoria', 'destacado')
    search_fields = ('nombre',)

# Agregamos esto para las Promociones
@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'etiqueta', 'activa')
    list_filter = ('activa',)