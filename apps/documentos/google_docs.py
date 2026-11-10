import requests

URL_DOCUMENTOS = "https://docs.googleapis.com/v1/documents/{documento_id}"


class ErrorGoogleDocs(Exception):
    """Google respondió con un código de error."""

    def __init__(self, codigo):
        super().__init__(f"Google Docs respondió con el código {codigo}")
        self.codigo = codigo


def obtener_datos_basicos(documento_id, access_token):
    """Pide a Google Docs solo el ID y el título del documento."""
    respuesta = requests.get(
        URL_DOCUMENTOS.format(documento_id=documento_id),
        headers={"Authorization": f"Bearer {access_token}"},
        params={"fields": "documentId,title"},
        timeout=15,
    )
    if respuesta.status_code != 200:
        raise ErrorGoogleDocs(respuesta.status_code)
    return respuesta.json()