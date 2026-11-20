"""Carga el archivo general de instrucciones (CLAUDE.md) y el skill que corresponde a cada etapa.

    apps/agente/instrucciones/
    ├── CLAUDE.md                      archivo general de instrucciones
    └── skills/
        ├── revision-perfil/SKILL.md            propuesta del tema, perfil y capítulos del perfil
        └── revision-documento-final/SKILL.md   introducción y capítulos del documento al 100%

Cada SKILL.md empieza con un encabezado entre líneas '---' que indica su nombre,
su descripción y las etapas a las que se aplica. Una etapa puede usar más de un skill:
el documento final usa el del perfil (para sus capítulos) y el del documento final.
"""

from dataclasses import dataclass
from pathlib import Path

CARPETA = Path(__file__).resolve().parent / "instrucciones"


@dataclass(frozen=True)
class Skill:
    nombre: str
    descripcion: str
    etapas: tuple
    contenido: str


def _separar_encabezado(texto):
    """Separa el encabezado '---' ... '---' del cuerpo del skill."""
    if not texto.startswith("---"):
        return {}, texto
    _, encabezado, cuerpo = texto.split("---", 2)
    datos = {}
    for linea in encabezado.strip().splitlines():
        if ":" in linea:
            clave, valor = linea.split(":", 1)
            datos[clave.strip()] = valor.strip()
    return datos, cuerpo.strip()


def listar_skills(carpeta=CARPETA):
    skills = []
    for ruta in sorted((carpeta / "skills").glob("*/SKILL.md")):
        datos, cuerpo = _separar_encabezado(ruta.read_text(encoding="utf-8"))
        etapas = tuple(e.strip() for e in datos.get("etapas", "").split(",") if e.strip())
        skills.append(Skill(datos.get("name", ruta.parent.name), datos.get("description", ""), etapas, cuerpo))
    return skills


def skills_para_etapa(etapa, carpeta=CARPETA):
    """Todos los skills que se aplican a la etapa elegida."""
    skills = [skill for skill in listar_skills(carpeta) if etapa in skill.etapas]
    if not skills:
        raise LookupError(f"No hay un skill configurado para la etapa {etapa}.")
    return skills


def armar_instrucciones(etapa, carpeta=CARPETA):
    """Instrucciones del sistema: archivo general + solo los skills de la etapa elegida."""
    general = (carpeta / "CLAUDE.md").read_text(encoding="utf-8").strip()
    partes = [general] + [skill.contenido for skill in skills_para_etapa(etapa, carpeta)]
    return "\n\n---\n\n".join(partes)