from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class EmailBackend(ModelBackend):
    """
    Autentica contra el modelo User de Django usando el email en lugar del username.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # 'username' aquí puede ser el nombre de usuario O el email, 
        # dependiendo de qué campo usemos en el formulario html.
        try:
            # Buscamos un usuario cuyo email coincida (ignorando mayúsculas/minúsculas)
            user = User.objects.get(Q(email__iexact=username) | Q(username__iexact=username))
        except User.DoesNotExist:
            # Si no existe, retornamos None (autenticación fallida)
            return None
        except User.MultipleObjectsReturned:
            # Si por error hay más de un usuario con ese email, tomamos el primero
            user = User.objects.filter(email__iexact=username).order_by('id').first()

        # Verificamos si la contraseña es correcta y si el usuario puede estar activo
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None