"""Conexión con el modelo de lenguaje.

La clase Proveedor define lo que el sistema necesita de cualquier modelo:
  - ProveedorClaude usa la API de Claude con la API key del usuario.
  - ProveedorSimulado devuelve una respuesta de ejemplo, sin llamar a Claude y sin costo
    (solo para desarrollo, cuando AGENTE_SIMULADO = True en settings.py).
Para agregar otro proveedor en el futuro, basta con otra clase que implemente el mismo método.
"""

import json
import re
from dataclasses import dataclass

import anthropic
from django.conf import settings

from .esquema import ESQUEMA_REVISION


@dataclass
class RespuestaModelo:
    texto: str
    tokens_entrada: int
    tokens_salida: int
    motivo_fin: str
    simulado: bool = False


class ErrorProveedor(Exception):
    """Error al comunicarse con el modelo, con un mensaje para el usuario."""


class Proveedor:
    def revisar(self, instrucciones, documento, modelo):
        raise NotImplementedError


class ProveedorClaude(Proveedor):

    def __init__(self, api_key):
        self.cliente = anthropic.Anthropic(api_key=api_key, timeout=300, max_retries=2)

    def revisar(self, instrucciones, documento, modelo):
        try:
            respuesta = self.cliente.messages.create(
                model=modelo,
                max_tokens=settings.MAX_TOKENS_SALIDA,
                system=instrucciones,
                messages=[{"role": "user", "content": documento}],
                output_config={
                    "effort": settings.ESFUERZO_AGENTE,
                    "format": {"type": "json_schema", "schema": ESQUEMA_REVISION},
                },
            )
        except anthropic.AuthenticationError:
            raise ErrorProveedor("La API key no es válida. Revísala en la Claude Console y vuelve a registrarla.")
        except anthropic.PermissionDeniedError:
            raise ErrorProveedor("La API key no tiene permiso para usar este modelo.")
        except anthropic.PaymentRequiredError:
            raise ErrorProveedor("La cuenta de la API key no tiene crédito. Carga crédito en la Claude Console.")
        except anthropic.NotFoundError:
            raise ErrorProveedor("El modelo seleccionado no está disponible para esta API key.")
        except anthropic.RateLimitError:
            raise ErrorProveedor("Se alcanzó el límite de solicitudes de la API key. Espera un momento e intenta de nuevo.")
        except (anthropic.RequestTooLargeError, anthropic.ContentTooLargeError):
            raise ErrorProveedor("El documento es demasiado grande para enviarlo en una sola revisión.")
        except anthropic.BadRequestError as error:
            if "credit" in str(error).lower():
                raise ErrorProveedor("La cuenta de la API key no tiene crédito. Carga crédito en la Claude Console.")
            raise ErrorProveedor("Claude rechazó la solicitud. Intenta de nuevo o elige otro modelo.")
        except (anthropic.APIConnectionError, anthropic.APITimeoutError):
            raise ErrorProveedor("No se pudo conectar con Claude. Revisa tu conexión e intenta de nuevo.")
        except anthropic.APIStatusError:
            raise ErrorProveedor("Claude no está disponible en este momento. Intenta de nuevo en unos minutos.")

        texto = "".join(bloque.text for bloque in respuesta.content if bloque.type == "text")
        return RespuestaModelo(
            texto=texto,
            tokens_entrada=respuesta.usage.input_tokens,
            tokens_salida=respuesta.usage.output_tokens,
            motivo_fin=respuesta.stop_reason,
        )


class ProveedorSimulado(Proveedor):
    """Devuelve una revisión de ejemplo con el mismo formato que Claude. No evalúa el documento."""

    def revisar(self, instrucciones, documento, modelo):
        # Toma la primera oración larga de un párrafo normal del documento, para mostrar un fragmento real.
        contenido = documento.split("<documento>", 1)[-1].split("</documento>", 1)[0]
        parrafos = [linea.strip() for linea in contenido.splitlines()
                    if linea.strip() and not linea.strip().startswith(("#", "|", "-", "["))]
        oraciones = [o for p in parrafos for o in re.split(r"(?<=[.!?])\s+", p) if len(o) > 40]
        fragmento = oraciones[0] if oraciones else ""
        datos = {
            "datos_generales": {
                "tipo_documento": "Ejemplo (modo simulado)",
                "objeto_estudio": "No identificado (modo simulado)",
                "campo_accion": "No identificado (modo simulado)",
                "causas": ["Ejemplo de causa"],
                "termino_relacion": "Ejemplo de término de relación",
                "efectos": ["Ejemplo de efecto"],
            },
            "observaciones": [
                {"seccion": "2.2. Formulación del problema", "regla": "FP-4", "fragmento": "",
                 "descripcion": "Observación de ejemplo: así se mostraría una causa redactada como carencia.",
                 "severidad": "CRITICA"},
                {"seccion": "1.1. Antecedentes Organizacionales", "regla": "ANT-1", "fragmento": fragmento,
                 "descripcion": "Observación de ejemplo con un fragmento tomado del documento.",
                 "severidad": "MAYOR"},
                {"seccion": "3.1. Objetivo General", "regla": "OG-5", "fragmento": "",
                 "descripcion": "Observación de ejemplo de severidad menor.", "severidad": "MENOR"},
            ],
        }
        texto = json.dumps(datos, ensure_ascii=False)
        return RespuestaModelo(
            texto=texto,
            tokens_entrada=(len(instrucciones) + len(documento)) // 4,
            tokens_salida=len(texto) // 4,
            motivo_fin="end_turn",
            simulado=True,
        )


def obtener_proveedor(api_key):
    """Elige el proveedor según la configuración: el simulado en desarrollo o Claude."""
    if getattr(settings, "AGENTE_SIMULADO", False):
        return ProveedorSimulado()
    return ProveedorClaude(api_key)