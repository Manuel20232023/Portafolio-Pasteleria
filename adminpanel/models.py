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
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción"
    )
    imagen = models.ImageField(
        upload_to='productos/',
        null=True,
        blank=True
    )
    stock = models.PositiveIntegerField(default=0)
    destacado = models.BooleanField(
        default=False,
        help_text="Mostrar en inicio"
    )

    def __str__(self):
        return self.nombre


class Promocion(models.Model):
    TIPO_CHOICES = [
        ('2x1', '2x1'),
        ('porcentaje', 'Descuento porcentaje'),
        ('segunda_unidad', 'Descuento en segunda unidad'),
    ]

    CATEGORIAS_OBJETIVO = [
        ('', 'Solo este producto'),
        ('vitrina', 'Repostería de vitrina'),
        ('postres', 'Postres'),
        ('tortas', 'Tortas'),
        ('all', 'Todas las categorías'),
    ]

    ENLACE_CATEGORIA_CHOICES = [
        ('', 'Sin categoria'),
        ('vitrina', 'Repostería de vitrina'),
        ('postres', 'Postres'),
        ('tortas', 'Tortas'),
    ]

    titulo = models.CharField(max_length=100)

    etiqueta = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        default='',
        help_text="Texto corto que se muestra como badge (ej: '2x1', '-30%'). Opcional."
    )

    descripcion = models.TextField(
        blank=True,
        null=True,
        default='',
        help_text="Descripción visible para el cliente. Opcional."
    )

    imagen = models.ImageField(
        upload_to='promos/',
        blank=True,
        null=True,
        help_text="Imagen opcional para la tarjeta de promoción."
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        help_text="Tipo de promoción (2x1, porcentaje, segunda unidad)."
    )

    porcentaje = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Solo para tipo 'porcentaje'. Ej: 20 para 20%."
    )

    porcentaje_segunda_unidad = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Solo para tipo 'segunda_unidad'. Ej: 50 para 50% en la segunda unidad."
    )

    producto = models.ForeignKey(
        'Producto',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="Producto específico al que se aplica la promo. Déjalo vacío si usarás una categoría."
    )

    categoria_objetivo = models.CharField(
        max_length=20,
        choices=CATEGORIAS_OBJETIVO,
        blank=True,
        default='',
        help_text="Si eliges una categoría, la promo se aplica a TODOS los productos de esa categoría."
    )

    enlace_categoria = models.CharField(
        max_length=20,
        choices=ENLACE_CATEGORIA_CHOICES,
        blank=True,
        default='',
        help_text="Categoría a la que apuntará el botón en la web. Opcional."
    )

    activo_desde = models.DateField(
        blank=True,
        null=True,
        help_text="Fecha desde la que la promo está activa. Opcional."
    )

    activo_hasta = models.DateField(
        blank=True,
        null=True,
        help_text="Fecha hasta la que la promo está activa. Opcional."
    )

    hasta_agotar_stock = models.BooleanField(
        default=False,
        help_text="Si se marca, la promo se desactiva cuando el producto se queda sin stock."
    )

    activa = models.BooleanField(
        default=True,
        help_text="Marca si la promo está activa."
    )

    vigencia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default='',
        help_text="Texto informativo (ej: 'Hasta el 30/06 o hasta agotar stock'). Opcional."
    )

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
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='pagado'
    )

    tipo_entrega = models.CharField(
        max_length=20,
        choices=TIPOS_ENTREGA,
        default='retiro'
    )
    direccion = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    def __str__(self):
        return f"Pedido {self.id} - {self.usuario.username}"


class DetallePedido(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        related_name='detalles',
        on_delete=models.CASCADE
    )
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.IntegerField()

    def subtotal(self):
        return self.cantidad * self.precio_unitario


class Pastel(models.Model):
    id_pasteles = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=20)
    descripcion = models.CharField(max_length=255)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    imagen = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.nombre


class Boleta(models.Model):
    id_boleta = models.AutoField(primary_key=True)
    costo_final = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField()

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)

    def __str__(self):
        return f"Boleta #{self.id_boleta}"
