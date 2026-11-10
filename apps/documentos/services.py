import re
from urllib.parse import parse_qs, urlparse

PATRON_ID = re.compile(r"/document(?:/u/\d+)?/d/([A-Za-z0-9_-]{25,})")


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
        raise ValueError(
            "El enlace corresponde a un archivo de Word guardado en Drive. "
            "Ábrelo en Google Docs y usa Archivo > Guardar como documento de Google Docs."
        )

    coincidencia = PATRON_ID.search(url.path)
    if not coincidencia:
        raise ValueError("No se encontró el identificador del documento en el enlace.")
    return coincidencia.group(1)