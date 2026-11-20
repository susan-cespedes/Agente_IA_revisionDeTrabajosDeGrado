import json
import re
from dataclasses import dataclass, field

from django.conf import settings
from django.db import transaction

from .cargador import armar_instrucciones
from .esquema import SEVERIDADES
from .models import ObservacionRevision, Revision
from .proveedores import ErrorProveedor, obtener_proveedor

ORDEN_SEVERIDAD = {s: i for i, s in enumerate(SEVERIDADES)}
NOMBRE_SEVERIDAD = {"CRITICA": "Crítica", "MAYOR": "Mayor", "MENOR": "Menor"}


@dataclass
class Observacion:
    seccion: str
    regla: str
    fragmento: str
    descripcion: str
    severidad: str
    fragmento_encontrado: bool = True

    @property
    def severidad_texto(self):
        return NOMBRE_SEVERIDAD[self.severidad]


@dataclass
class ResultadoRevision:
    datos_generales: dict
    observaciones: list = field(default_factory=list)
    modelo: str = ""
    tokens_entrada: int = 0
    tokens_salida: int = 0
    simulado: bool = False

    @property
    def costo_estimado(self):
        precios = settings.MODELOS_AGENTE.get(self.modelo, {})
        return (self.tokens_entrada * precios.get("precio_entrada", 0)
                + self.tokens_salida * precios.get("precio_salida", 0)) / 1_000_000

    @property
    def conteo(self):
        return {s: sum(1 for o in self.observaciones if o.severidad == s) for s in SEVERIDADES}


def _normalizar(texto):
    """Minúsculas, comillas y espacios unificados, para comparar fragmentos con el documento."""
    texto = texto.lower()
    for a, b in (("“", '"'), ("”", '"'), ("‘", "'"), ("’", "'"), ("–", "-"), ("—", "-")):
        texto = texto.replace(a, b)
    return re.sub(r"\s+", " ", texto).strip()


def fragmento_existe(fragmento, texto_documento):
    """True si el fragmento citado aparece en el documento (o si está vacío, por ser una ausencia)."""
    if not fragmento.strip():
        return True
    return _normalizar(fragmento).strip(" .\"'") in _normalizar(texto_documento)


def armar_mensaje(documento, etapa, modalidad):
    """El mensaje que recibe el agente: etapa, modalidad, título y el documento leído."""
    return (f"Etapa del trabajo de grado: {Revision.Etapa(etapa).label}\n"
            f"Modalidad: {Revision.Modalidad(modalidad).label}\n"
            f"Título del documento: {documento.titulo}\n\n"
            f"<documento>\n{documento.texto}\n</documento>")


def revisar_documento(documento, etapa, modalidad, modelo, api_key, proveedor=None):
    """Envía el documento al agente con las instrucciones de la etapa y devuelve sus observaciones."""
    if modelo not in settings.MODELOS_AGENTE:
        raise ValueError("El modelo seleccionado no está disponible.")
    proveedor = proveedor or obtener_proveedor(api_key)

    respuesta = proveedor.revisar(armar_instrucciones(etapa), armar_mensaje(documento, etapa, modalidad), modelo)

    if respuesta.motivo_fin == "max_tokens":
        raise ErrorProveedor("La respuesta del agente quedó incompleta por su longitud. Intenta de nuevo.")
    if respuesta.motivo_fin == "refusal":
        raise ErrorProveedor("El modelo no completó la revisión de este documento.")
    try:
        datos = json.loads(respuesta.texto)
    except json.JSONDecodeError:
        raise ErrorProveedor("La respuesta del agente no tiene el formato esperado. Intenta de nuevo.")

    observaciones = []
    for o in datos.get("observaciones", []):
        severidad = str(o.get("severidad", "MENOR")).upper()
        if severidad not in ORDEN_SEVERIDAD:
            severidad = "MENOR"
        observaciones.append(Observacion(
            seccion=o.get("seccion", ""),
            regla=o.get("regla", ""),
            fragmento=o.get("fragmento", ""),
            descripcion=o.get("descripcion", ""),
            severidad=severidad,
            fragmento_encontrado=fragmento_existe(o.get("fragmento", ""), documento.texto),
        ))
    observaciones.sort(key=lambda o: ORDEN_SEVERIDAD[o.severidad])

    return ResultadoRevision(
        datos_generales=datos.get("datos_generales", {}),
        observaciones=observaciones,
        modelo=modelo,
        tokens_entrada=respuesta.tokens_entrada,
        tokens_salida=respuesta.tokens_salida,
        simulado=respuesta.simulado,
    )


def guardar_revision(usuario, documento_id, titulo, etapa, modalidad, resultado):
    """Guarda la revisión con sus datos generales y sus observaciones, y la devuelve."""
    with transaction.atomic():
        revision = Revision.objects.create(
            usuario=usuario, documento_id=documento_id, nombre_documento=titulo[:255], etapa=etapa,
            modalidad=modalidad, modelo=resultado.modelo, tokens_entrada=resultado.tokens_entrada,
            tokens_salida=resultado.tokens_salida, cantidad_observaciones=len(resultado.observaciones),
            datos_generales=resultado.datos_generales, simulado=resultado.simulado,
        )
        ObservacionRevision.objects.bulk_create([
            ObservacionRevision(
                revision=revision, orden=posicion, seccion=o.seccion[:255], regla=o.regla[:20],
                fragmento=o.fragmento, descripcion=o.descripcion, severidad=o.severidad,
                fragmento_encontrado=o.fragmento_encontrado,
            )
            for posicion, o in enumerate(resultado.observaciones, start=1)
        ])
    return revision