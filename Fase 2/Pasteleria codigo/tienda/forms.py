from django import forms
from django.contrib.auth.models import User
from .models import Perfil

class RegistroForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    telefono = forms.CharField(max_length=15, required=True)
    direccion = forms.CharField(max_length=200, required=True)
    ciudad = forms.CharField(max_length=100, required=True)
    fecha_nacimiento = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    recibir_ofertas = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            Perfil.objects.create(
                user=user,
                telefono=self.cleaned_data['telefono'],
                direccion=self.cleaned_data['direccion'],
                ciudad=self.cleaned_data['ciudad'],
                fecha_nacimiento=self.cleaned_data.get('fecha_nacimiento'),
                recibir_ofertas=self.cleaned_data.get('recibir_ofertas', False),
            )
        return user
