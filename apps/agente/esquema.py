"""Esquema JSON que Claude debe respetar al responder (salidas estructuradas)."""

SEVERIDADES = ["CRITICA", "MAYOR", "MENOR"]

ESQUEMA_REVISION = {
    "type": "object",
    "properties": {
        "datos_generales": {
            "type": "object",
            "properties": {
                "tipo_documento": {"type": "string"},
                "objeto_estudio": {"type": "string"},
                "campo_accion": {"type": "string"},
                "causas": {"type": "array", "items": {"type": "string"}},
                "termino_relacion": {"type": "string"},
                "efectos": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["tipo_documento", "objeto_estudio", "campo_accion", "causas",
                         "termino_relacion", "efectos"],
            "additionalProperties": False,
        },
        "observaciones": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "seccion": {"type": "string"},
                    "regla": {"type": "string"},
                    "fragmento": {"type": "string"},
                    "descripcion": {"type": "string"},
                    "severidad": {"type": "string", "enum": SEVERIDADES},
                },
                "required": ["seccion", "regla", "fragmento", "descripcion", "severidad"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["datos_generales", "observaciones"],
    "additionalProperties": False,
}