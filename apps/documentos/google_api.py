import logging

import requests

logger = logging.getLogger(__name__)

URL_DRIVE_ARCHIVO = "https://www.googleapis.com/drive/v3/files/{documento_id}"
URL_DOCS_DOCUMENTO = "https://docs.googleapis.com/v1/documents/{documento_id}"


class ErrorGoogle(Exception):
    """Google respondió con un código de error.

    codigo: código HTTP (400, 401, 403, 404...).
    razon: motivo que da Google, p. ej. SERVICE_DISABLED o ACCESS_TOKEN_SCOPE_INSUFFICIENT.
    """

    def __init__(self, codigo, razon=""):
        super().__init__(f"Google respondió con el código {codigo} ({razon})")
        self.codigo = codigo
        self.razon = razon


def _razon_del_error(respuesta):
    """Extrae el motivo del error de la respuesta JSON de Google, si lo trae."""
    try:
        error = respuesta.json().get("error", {})
    except ValueError:
        return ""
    for detalle in error.get("details", []) + error.get("errors", []):
        if detalle.get("reason"):
            return detalle["reason"]
    return error.get("status", "")


def _get(url, access_token, params):
    """Hace la petición a Google y lanza ErrorGoogle si la respuesta no es exitosa."""
    respuesta = requests.get(url, headers={"Authorization": f"Bearer {access_token}"},
                             params=params, timeout=15)
    if respuesta.status_code != 200:
        razon = _razon_del_error(respuesta)
        # Se registra el código y el motivo (nunca el token) para diagnosticar en la terminal.
        logger.warning("Google respondió %s (%s) en %s", respuesta.status_code, razon, url)
        raise ErrorGoogle(respuesta.status_code, razon)
    return respuesta.json()


def obtener_metadatos(documento_id, access_token):
    """Pide a Google Drive el nombre y el tipo (mimeType) del archivo, sin su contenido."""
    return _get(
        URL_DRIVE_ARCHIVO.format(documento_id=documento_id),
        access_token,
        {"fields": "id,name,mimeType", "supportsAllDrives": "true"},
    )


def obtener_documento(documento_id, access_token):
    """Pide a Google Docs el documento completo (estructura y texto) en formato JSON."""
    return _get(URL_DOCS_DOCUMENTO.format(documento_id=documento_id), access_token, {})