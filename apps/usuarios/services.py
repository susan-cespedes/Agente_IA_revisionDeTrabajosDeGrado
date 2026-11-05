import re

from django.conf import settings

from .models import Usuario


def es_correo_institucional(email):
    """True si el correo pertenece al dominio de la universidad (o a un subdominio)."""
    dominio = email.strip().lower().rsplit("@", 1)[-1]
    institucional = settings.DOMINIO_INSTITUCIONAL.lower()
    return dominio == institucional or dominio.endswith("." + institucional)


def rol_segun_correo(email):
    """Identifica el rol a partir del formato del correo institucional."""
    if re.match(settings.PATRON_CORREO_DOCENTE, email.strip().lower()):
        return Usuario.Rol.DOCENTE
    return Usuario.Rol.ESTUDIANTE


def obtener_o_crear_usuario(email, nombre="", apellido=""):
    """Devuelve el usuario con ese correo; si no existe, lo crea con su rol.

    No hay registro propio: el usuario se crea la primera vez que ingresa con Google.
    """
    email = email.strip().lower()
    if not es_correo_institucional(email):
        raise PermissionError("Solo se permite el ingreso con la cuenta institucional de la UCB.")

    usuario, creado = Usuario.objects.get_or_create(
        email=email,
        defaults={
            "username": email,
            "first_name": nombre,
            "last_name": apellido,
            "rol": rol_segun_correo(email),
        },
    )
    if creado:
        usuario.set_unusable_password()  # nunca entra con contraseña, solo con Google
        usuario.save()
    return usuario