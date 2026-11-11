import re
from urllib.parse import parse_qs, urlparse

import requests

from .google_api import ErrorGoogle, obtener_documento, obtener_metadatos
from .lector import leer_estructura

PATRON_ID = re.compile(r"/document(?:/u/\d+)?/d/([A-Za-z0-9_-]{25,})")

# Tipo que Google Drive asigna a los documentos nativos de Google Docs.
MIME_GOOGLE_DOCS = "application/vnd.google-apps.document"

MENSAJE_NO_NATIVO = ("Solo se permiten documentos nativos de Google Docs. Este archivo es un Word u otro formato "
                     "guardado en Drive: ábrelo y usa Archivo > Guardar como documento de Google Docs.")

MENSAJES_ERROR_GOOGLE = {
    401: "Tu sesión con Google venció. Sal del sistema y vuelve a ingresar.",
    403: "No tienes permiso para abrir este documento. Pide al propietario que lo comparta con tu cuenta institucional.",
    404: "No se encontró el documento o no tienes permiso para abrirlo. Revisa el enlace y que esté compartido "
         "con tu cuenta institucional.",
}

# Algunos errores 403 no son por permisos del documento, sino por la configuración o el consentimiento.
MENSAJES_RAZON_GOOGLE = {
    "SERVICE_DISABLED": "Una API de Google que usa el sistema no está habilitada en su proyecto de Google Cloud. "
                        "Avisa al administrador.",
    "accessNotConfigured": "Una API de Google que usa el sistema no está habilitada en su proyecto de Google Cloud. "
                           "Avisa al administrador.",
    "ACCESS_TOKEN_SCOPE_INSUFFICIENT": "No diste al sistema todos los permisos que necesita en Google. "
                                       "Sal del sistema, vuelve a ingresar y acepta los permisos.",
    "insufficientPermissions": "No diste al sistema todos los permisos que necesita en Google. "
                               "Sal del sistema, vuelve a ingresar y acepta los permisos.",
}


def extraer_id_documento(enlace):
    """Devuelve el ID de un documento de Google Docs a partir de su enlace.

    Lanza ValueError con un mensaje para el usuario si el enlace no es válido.
    """
    enlace = (enlace or "").strip()
    url = urlparse(enlace)

    if url.scheme != "https" or url.netloc != "docs.google.com":
        raise ValueError("El enlace debe ser de un documento de Google Docs (https://docs.google.com/document/...).")

    if not url.path.startswith("/document/"):
        raise ValueError("El enlace no corresponde a un documento de texto de Google Docs.")

    if parse_qs(url.query).get("rtpof") == ["true"]:
        raise ValueError(MENSAJE_NO_NATIVO)

    coincidencia = PATRON_ID.search(url.path)
    if not coincidencia:
        raise ValueError("No se encontró el identificador del documento en el enlace.")
    return coincidencia.group(1)


def _mensaje_de_error(error):
    """Traduce un error de Google a un mensaje para el usuario."""
    return MENSAJES_RAZON_GOOGLE.get(error.razon) or MENSAJES_ERROR_GOOGLE.get(
        error.codigo, "Google no respondió correctamente. Intenta de nuevo en unos minutos.")


def verificar_documento(documento_id, access_token):
    """Confirma con Google Drive que el archivo existe, el usuario puede abrirlo y es un Google Docs nativo.

    Devuelve el nombre del documento o lanza ValueError con un mensaje para el usuario.
    """
    if not access_token:
        raise ValueError(MENSAJES_ERROR_GOOGLE[401])
    try:
        datos = obtener_metadatos(documento_id, access_token)
    except ErrorGoogle as error:
        raise ValueError(_mensaje_de_error(error))
    except requests.RequestException:
        raise ValueError("No se pudo conectar con Google. Revisa tu conexión e intenta de nuevo.")

    if datos.get("mimeType") != MIME_GOOGLE_DOCS:
        raise ValueError(MENSAJE_NO_NATIVO)
    return datos["name"]


def leer_documento(documento_id, access_token):
    """Verifica el documento y lee su contenido. Devuelve un DocumentoLeido.

    El contenido no se guarda: se usa solo durante la solicitud (límite del perfil).
    """
    verificar_documento(documento_id, access_token)
    try:
        documento_json = obtener_documento(documento_id, access_token)
    except ErrorGoogle as error:
        raise ValueError(_mensaje_de_error(error))
    except requests.RequestException:
        raise ValueError("No se pudo conectar con Google. Revisa tu conexión e intenta de nuevo.")
    return leer_estructura(documento_json)