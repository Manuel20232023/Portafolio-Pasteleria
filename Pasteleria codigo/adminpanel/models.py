from django.db import models
from django.contrib.auth.models import User

class Producto(models.Model):
    CATEGORIAS = [
        ('vitrina', 'Repostería de vitrina'),
        ('tortas', 'Tortas'),
        ('postres', 'Postres'),
    ]

    nombre = models.CharField(max_length=100)
    precio = models.IntegerField(verbose_name="Precio")
    categoria = models.CharField(max_length=20, choices=CATEGORIAS)
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    destacado = models.BooleanField(default=False, help_text="Mostrar en inicio")

    def __str__(self):
        return self.nombre
    
class Promocion(models.Model):
    titulo = models.CharField(max_length=200, verbose_name="Nombre de la Promoción")
    descripcion = models.TextField(verbose_name="Descripción corta")
    imagen = models.ImageField(upload_to='promos/', verbose_name="Banner o foto")
    etiqueta = models.CharField(max_length=50, help_text="Ej: '2x1', '-15%', 'Oferta'")
    vigencia = models.CharField(max_length=100, blank=True, null=True)
    descuento = models.CharField(max_length=50, blank=True, null=True)
    # Este campo sirve para que al hacer clic, lleve a una categoría (vitrina, tortas, postres)
    enlace_categoria = models.CharField(
        max_length=50, 
        choices=[('vitrina', 'Vitrina'), ('tortas', 'Tortas'), ('postres', 'Postres')],
        verbose_name="Enlace a categoría"
    )
    activa = models.BooleanField(default=True, verbose_name="¿Está activa?")

    def __str__(self):
        return self.titulo
    
class Pedido(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
    ]
    TIPOS_ENTREGA = [
        ('retiro', 'Retiro en tienda'),
        ('despacho', 'Despacho a domicilio'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.IntegerField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pagado')
    
    # Nuevos campos para soportar las pestañas del admin
    tipo_entrega = models.CharField(max_length=20, choices=TIPOS_ENTREGA, default='retiro')
    direccion = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Pedido #{self.id} - {self.usuario.username}"
    def __str__(self):
        return f"Pedido {self.id} - {self.usuario.username}"

class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.IntegerField() # Guardamos el precio al momento de la compra por si cambia después

    def subtotal(self):
        return self.cantidad * self.precio_unitario