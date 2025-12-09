from django import forms
from django.core.exceptions import ValidationError
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


def _clean_logica_promocion(cleaned):
    """
    Lógica compartida de validación para Promocion.
    Se usa tanto en PromocionForm (panel) como en PromocionAdminForm (Django admin).
    """
    tipo = cleaned.get("tipo")
    pct = cleaned.get("porcentaje")
    pct2 = cleaned.get("porcentaje_segunda_unidad")

    errors = {}

    if tipo == "2x1":
        # en 2x1 no debe haber porcentajes
        if pct:
            errors["porcentaje"] = ValidationError(
                "En una promo 2x1 deja este campo vacío."
            )
        if pct2:
            errors["porcentaje_segunda_unidad"] = ValidationError(
                "En una promo 2x1 no se usa % en la segunda unidad."
            )

    elif tipo == "porcentaje":
        # debe tener porcentaje general, pero NO % segunda unidad
        if not pct:
            errors["porcentaje"] = ValidationError(
                "Debes indicar el porcentaje de descuento."
            )
        if pct2:
            errors["porcentaje_segunda_unidad"] = ValidationError(
                "No uses este campo en una promo de tipo 'Descuento %'."
            )

    elif tipo == "segunda_unidad":
        # debe tener % segunda unidad, pero NO porcentaje general
        if not pct2:
            errors["porcentaje_segunda_unidad"] = ValidationError(
                "Debes indicar el % de descuento en la segunda unidad."
            )
        if pct:
            errors["porcentaje"] = ValidationError(
                "No uses el porcentaje general en una promo de tipo 'Segunda unidad'."
            )

    if errors:
        raise ValidationError(errors)

    return cleaned


class PromocionForm(forms.ModelForm):
    class Meta:
        model = Promocion
        fields = [
            'titulo', 'descripcion', 'imagen',
            'producto', 'tipo', 'porcentaje', 'porcentaje_segunda_unidad',
            'activo_desde', 'activo_hasta', 'hasta_agotar_stock',
            'etiqueta', 'vigencia', 'enlace_categoria', 'activa', 'categoria_objetivo'
        ]
        widgets = {
            'activo_desde': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'activo_hasta': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def clean(self):
        cleaned = super().clean()
        return _clean_logica_promocion(cleaned)


class PromocionAdminForm(forms.ModelForm):
    class Meta:
        model = Promocion
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        return _clean_logica_promocion(cleaned)
