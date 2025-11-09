from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm # Importamos esto para heredar
from .models import Perfil

# === 1. NUEVO FORMULARIO DE LOGIN CON EMAIL ===
class EmailAuthenticationForm(AuthenticationForm):
    # Sobrescribimos el campo username para que ahora sea para el email
    username = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'autofocus': True})
    )

# === 2. ACTUALIZACIÓN DEL FORMULARIO DE REGISTRO ===
class RegistroForm(forms.ModelForm):
    # Hacemos el email obligatorio y validamos que sea único
    email = forms.EmailField(required=True, label="Correo electrónico")

    # ... (resto de tus campos: password, telefono, etc.) ...
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirmar contraseña")
    telefono = forms.CharField(max_length=15, required=True, label="Teléfono")
    direccion = forms.CharField(max_length=200, required=True, label="Dirección")
    ciudad = forms.CharField(max_length=100, required=True, label="Ciudad")
    fecha_nacimiento = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Fecha de nacimiento"
    )
    recibir_ofertas = forms.BooleanField(required=False, label="Deseo recibir ofertas")

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']
        # username lo seguimos pidiendo porque Django lo exige internamente,
        # pero el usuario principal para loguearse será el email.

    # Validación personalizada para asegurar que el email sea único
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
             raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            # Si no coinciden, agregamos un error al campo 'password_confirm'
            self.add_error('password_confirm', "Las contraseñas no coinciden.")
        return cleaned_data

    def save(self, commit=True):
        # ... (tu método save actual está bien, mantenlo igual) ...
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
