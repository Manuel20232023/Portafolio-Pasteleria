from django import forms
from .models import Producto, Promocion

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'precio', 'stock', 'categoria', 'imagen', 'descripcion', 'destacado']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'destacado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
class PromocionForm(forms.ModelForm):
    class Meta:
        model = Promocion
        # Usamos los nombres REALES que tienen tus columnas en la BD
        fields = ['titulo', 'descripcion', 'etiqueta', 'enlace_categoria', 'imagen', 'activa']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'etiqueta': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 20% OFF, 2x1'}),
            'enlace_categoria': forms.Select(attrs={'class': 'form-select'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }