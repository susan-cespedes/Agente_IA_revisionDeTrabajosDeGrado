import logging

import requests

logger = logging.getLogger(__name__)

URL_DOCUMENTOS = "https://docs.googleapis.com/v1/documents/{documento_id}"


class ErrorGoogleDocs(Exception):
    """Google respondió con un código de error.

    codigo: código HTTP (400, 401, 403, 404...).
    razon: motivo que da Google, p. ej. SERVICE_DISABLED o ACCESS_TOKEN_SCOPE_INSUFFICIENT.
    """

    def __init__(self, codigo, razon=""):
        super().__init__(f"Google Docs respondió con el código {codigo} ({razon})")
        self.codigo = codigo
        self.razon = razon


def _razon_del_error(respuesta):
    """Extrae el motivo del error de la respuesta JSON de Google, si lo trae."""
    try:
        error = respuesta.json().get("error", {})
    except ValueError:
        return ""
    for detalle in error.get("details", []):
        if detalle.get("reason"):
            return detalle["reason"]
    return error.get("status", "")


def obtener_datos_basicos(documento_id, access_token):
    """Pide a Google Docs solo el ID y el título del documento."""
    respuesta = requests.get(
        URL_DOCUMENTOS.format(documento_id=documento_id),
        headers={"Authorization": f"Bearer {access_token}"},
        params={"fields": "documentId,title"},
        timeout=15,
    )
    if respuesta.status_code != 200:
        razon = _razon_del_error(respuesta)
        # Se registra el código y el motivo (nunca el token) para diagnosticar en la terminal.
        logger.warning("Google Docs respondió %s (%s) para el documento %s",
                       respuesta.status_code, razon, documento_id)
        raise ErrorGoogleDocs(respuesta.status_code, razon)
    return respuesta.json()