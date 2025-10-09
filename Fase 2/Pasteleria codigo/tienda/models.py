from django.contrib.auth.models import User
from django.db import models

class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefono = models.CharField(max_length=15)
    direccion = models.CharField(max_length=200)
    ciudad = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    recibir_ofertas = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username
