"""Convierte el JSON que devuelve la API de Google Docs en texto ordenado para el agente.

Google Docs entrega el documento como una lista de elementos (párrafos, tablas, saltos).
Aquí se recorren en orden y se arma:
  - el texto completo, con los títulos marcados con # según su nivel y las tablas como filas | a | b |;
  - la lista de secciones (títulos con estilo de encabezado);
  - conteos de palabras, tablas e imágenes.
"""

from dataclasses import dataclass, field

NIVEL_ENCABEZADO = {f"HEADING_{n}": n for n in range(1, 7)}
NIVEL_ENCABEZADO["TITLE"] = 1


@dataclass
class Seccion:
    nivel: int
    titulo: str


@dataclass
class DocumentoLeido:
    titulo: str
    texto: str
    secciones: list = field(default_factory=list)
    palabras: int = 0
    tablas: int = 0
    imagenes: int = 0


def _texto_del_parrafo(parrafo):
    """Une los fragmentos de texto de un párrafo y cuenta sus imágenes."""
    partes, imagenes = [], 0
    for elemento in parrafo.get("elements", []):
        if "textRun" in elemento:
            partes.append(elemento["textRun"].get("content", ""))
        elif "inlineObjectElement" in elemento:
            partes.append("[imagen]")
            imagenes += 1
    return "".join(partes).replace("\u000b", "\n").strip(), imagenes


def _recorrer(elementos, lineas, secciones, conteo):
    for elemento in elementos:
        if "paragraph" in elemento:
            parrafo = elemento["paragraph"]
            texto, imagenes = _texto_del_parrafo(parrafo)
            conteo["imagenes"] += imagenes
            if not texto:
                continue
            estilo = parrafo.get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
            nivel = NIVEL_ENCABEZADO.get(estilo)
            if nivel:
                secciones.append(Seccion(nivel, texto))
                lineas.append(f"{'#' * nivel} {texto}")
            elif "bullet" in parrafo:
                lineas.append(f"- {texto}")
            else:
                lineas.append(texto)

        elif "table" in elemento:
            conteo["tablas"] += 1
            for fila in elemento["table"].get("tableRows", []):
                celdas = []
                for celda in fila.get("tableCells", []):
                    sub_lineas = []
                    _recorrer(celda.get("content", []), sub_lineas, [], conteo)
                    celdas.append(" ".join(sub_lineas).replace("|", "/"))
                lineas.append("| " + " | ".join(celdas) + " |")


def leer_estructura(documento_json):
    """Recibe el JSON de Google Docs y devuelve un DocumentoLeido."""
    lineas, secciones = [], []
    conteo = {"tablas": 0, "imagenes": 0}
    _recorrer(documento_json.get("body", {}).get("content", []), lineas, secciones, conteo)
    texto = "\n".join(lineas)
    return DocumentoLeido(
        titulo=documento_json.get("title", ""),
        texto=texto,
        secciones=secciones,
        palabras=len(texto.split()),
        tablas=conteo["tablas"],
        imagenes=conteo["imagenes"],
    )