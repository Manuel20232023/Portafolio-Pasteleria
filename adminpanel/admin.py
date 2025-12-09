"""
from django.contrib import admin
from .models import Producto, Promocion # Importamos ambos

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio', 'stock', 'destacado')
    list_filter = ('categoria', 'destacado')
    search_fields = ('nombre',)

@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'etiqueta', 'activa')
    list_filter = ('activa',)

"""
from django.contrib import admin
from .models import Producto, Promocion, Pedido, DetallePedido, Boleta
from .forms import PromocionAdminForm
# ---------------------------
# ADMIN DE PRODUCTO
# ---------------------------
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'categoria', 'stock', 'destacado')
    list_filter = ('categoria', 'destacado')
    search_fields = ('nombre',)
    list_editable = ('precio', 'stock', 'destacado')


# ---------------------------
# ADMIN DE PROMOCION
# ---------------------------
@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    form = PromocionAdminForm

    list_display = ("titulo", "tipo", "producto", "categoria_objetivo", "activa")
    list_filter = ("tipo", "categoria_objetivo", "activa")
    search_fields = ("titulo", "etiqueta", "producto__nombre")

    fieldsets = (
        ("Datos generales", {
            "fields": ("titulo", "etiqueta", "descripcion", "imagen"),
            "description": "Nombre visible de la promo, etiqueta corta y descripción opcional."
        }),
        ("¿A qué aplica?", {
            "fields": ("producto", "categoria_objetivo"),
            "description": (
                "Puedes dejar <strong>solo producto</strong> para una promo puntual, "
                "o elegir una <strong>categoría objetivo</strong> "
                "para aplicar la promo a toda la categoría."
            )
        }),
        ("Tipo de promoción", {
            "fields": ("tipo", "porcentaje", "porcentaje_segunda_unidad"),
            "description": (
                "<ul>"
                "<li><strong>2x1</strong>: se cobra solo 1 producto por cada 2 unidades.</li>"
                "<li><strong>Descuento %</strong>: descuento fijo sobre todas las unidades.</li>"
                "<li><strong>% en 2ª unidad</strong>: se aplica solo a la 2ª unidad de cada par.</li>"
                "</ul>"
                "Los campos de porcentaje se habilitan/deshabilitan automáticamente según el tipo."
            )
        }),
        ("Vigencia y estado", {
            "fields": ("activo_desde", "activo_hasta", "vigencia",
                       "enlace_categoria", "hasta_agotar_stock", "activa"),
        }),
    )

    class Media:
        js = ("adminpanel/js/promocion_admin.js",)


# ---------------------------
# INLINE: detalle de pedidos
# ---------------------------
class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    readonly_fields = ('subtotal',)


# ---------------------------
# ADMIN DE PEDIDOS
# ---------------------------
@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'fecha', 'total', 'estado', 'tipo_entrega')
    list_filter = ('estado', 'tipo_entrega', 'fecha')
    search_fields = ('usuario__username',)
    inlines = [DetallePedidoInline]


# ---------------------------
# ADMIN DE DETALLE PEDIDO
# ---------------------------
@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'producto', 'cantidad', 'precio_unitario', 'subtotal')
    list_filter = ('producto',)


# ---------------------------
# ADMIN DE BOLETA
# ---------------------------
@admin.register(Boleta)
class BoletaAdmin(admin.ModelAdmin):
    list_display = ('id_boleta', 'pedido', 'costo_final', 'fecha')
    list_filter = ('fecha',)
    search_fields = ('pedido__id',)