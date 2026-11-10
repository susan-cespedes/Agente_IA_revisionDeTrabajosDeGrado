import re
from urllib.parse import parse_qs, urlparse

import requests

from .google_docs import ErrorGoogleDocs, obtener_datos_basicos

PATRON_ID = re.compile(r"/document(?:/u/\d+)?/d/([A-Za-z0-9_-]{25,})")

MENSAJES_ERROR_GOOGLE = {
    400: "El documento no es un documento nativo de Google Docs (por ejemplo, es un Word subido a Drive). "
         "Ábrelo en Google Docs y usa Archivo > Guardar como documento de Google Docs.",
    401: "Tu sesión con Google venció. Sal del sistema y vuelve a ingresar.",
    403: "No tienes permiso para abrir este documento. Pide al propietario que lo comparta con tu cuenta institucional.",
    404: "No se encontró el documento. Revisa que el enlace sea correcto.",
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
        raise ValueError(MENSAJES_ERROR_GOOGLE[400])

    coincidencia = PATRON_ID.search(url.path)
    if not coincidencia:
        raise ValueError("No se encontró el identificador del documento en el enlace.")
    return coincidencia.group(1)


def verificar_documento(documento_id, access_token):
    """Confirma con Google que el documento existe, es nativo y el usuario puede abrirlo.

    Devuelve el título del documento o lanza ValueError con un mensaje para el usuario.
    """
    if not access_token:
        raise ValueError(MENSAJES_ERROR_GOOGLE[401])
    try:
        datos = obtener_datos_basicos(documento_id, access_token)
    except ErrorGoogleDocs as error:
        raise ValueError(MENSAJES_ERROR_GOOGLE.get(
            error.codigo, "Google Docs no respondió correctamente. Intenta de nuevo en unos minutos."))
    except requests.RequestException:
        raise ValueError("No se pudo conectar con Google Docs. Revisa tu conexión e intenta de nuevo.")
    return datos["title"]