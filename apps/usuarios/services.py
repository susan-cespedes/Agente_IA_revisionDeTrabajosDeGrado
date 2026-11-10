import re

from django.conf import settings
from django.core.cache import caches

from .models import Usuario


# --- Usuarios y roles ---

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
    """Devuelve el usuario con ese correo; si no existe, lo crea con su rol."""
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


# --- API key del usuario (solo en memoria, durante la sesión) ---

_keys = caches["api_keys"]
PREFIJO_KEY_ANTHROPIC = "sk-ant-"


def _clave_cache(sesion):
    """Nombre con el que se guarda la key en la caché: único por sesión."""
    return f"api_key:{sesion.session_key}"


def formato_api_key_valido(api_key):
    """Revisa que el texto tenga la forma de una API key de Anthropic."""
    api_key = api_key.strip()
    return api_key.startswith(PREFIJO_KEY_ANTHROPIC) and len(api_key) > 40 and " " not in api_key


def guardar_api_key(sesion, api_key):
    """Guarda la key en memoria, asociada a la sesión. No toca la base de datos."""
    api_key = api_key.strip()
    if not formato_api_key_valido(api_key):
        raise ValueError("La API key no tiene el formato de una key de Anthropic (debe empezar con sk-ant-).")
    if sesion.session_key is None:
        sesion.save()
    _keys.set(_clave_cache(sesion), api_key)


def obtener_api_key(sesion):
    """Devuelve la key de esta sesión, o None si no hay una o ya venció."""
    if sesion.session_key is None:
        return None
    return _keys.get(_clave_cache(sesion))


def tiene_api_key(sesion):
    return obtener_api_key(sesion) is not None


def borrar_api_key(sesion):
    """Elimina la key de la memoria (se usa al cerrar sesión)."""
    if sesion.session_key is not None:
        _keys.delete(_clave_cache(sesion))


# --- Token de acceso de Google (solo en memoria, durante la sesión) ---

def guardar_token_google(sesion, access_token, expira_en_segundos):
    """Guarda el token en memoria hasta un minuto antes de que Google lo venza."""
    if sesion.session_key is None:
        sesion.save()
    duracion = max(int(expira_en_segundos) - 60, 60)
    _keys.set(f"google_token:{sesion.session_key}", access_token, timeout=duracion)


def obtener_token_google(sesion):
    if sesion.session_key is None:
        return None
    return _keys.get(f"google_token:{sesion.session_key}")


def borrar_token_google(sesion):
    if sesion.session_key is not None:
        _keys.delete(f"google_token:{sesion.session_key}")