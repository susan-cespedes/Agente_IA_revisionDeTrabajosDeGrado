"""Carga el archivo general de instrucciones (CLAUDE.md) y el skill que corresponde a cada etapa.

    apps/agente/instrucciones/
    ├── CLAUDE.md                      archivo general de instrucciones
    └── skills/
        └── revision-perfil/SKILL.md   skill de la propuesta del tema y del perfil (OE4)

Cada SKILL.md empieza con un encabezado entre líneas '---' que indica su nombre,
su descripción y las etapas a las que se aplica.
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
    """Devuelve todos los skills que hay en la carpeta skills/."""
    skills = []
    for ruta in sorted((carpeta / "skills").glob("*/SKILL.md")):
        datos, cuerpo = _separar_encabezado(ruta.read_text(encoding="utf-8"))
        etapas = tuple(e.strip() for e in datos.get("etapas", "").split(",") if e.strip())
        skills.append(Skill(datos.get("name", ruta.parent.name), datos.get("description", ""), etapas, cuerpo))
    return skills


def skill_para_etapa(etapa, carpeta=CARPETA):
    """Devuelve el skill que se aplica a la etapa indicada."""
    for skill in listar_skills(carpeta):
        if etapa in skill.etapas:
            return skill
    raise LookupError(f"No hay un skill configurado para la etapa {etapa}.")


def armar_instrucciones(etapa, carpeta=CARPETA):
    """Instrucciones del sistema: archivo general + solo el skill de la etapa elegida."""
    general = (carpeta / "CLAUDE.md").read_text(encoding="utf-8").strip()
    skill = skill_para_etapa(etapa, carpeta)
    return f"{general}\n\n---\n\n{skill.contenido}"