from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Usuario del sistema, identificado por su cuenta institucional de Google."""

    class Rol(models.TextChoices):
        DOCENTE = "DOCENTE", "Docente"
        ESTUDIANTE = "ESTUDIANTE", "Estudiante"

    email = models.EmailField("correo institucional", unique=True)
    rol = models.CharField(max_length=10, choices=Rol.choices, default=Rol.ESTUDIANTE)

    @property
    def es_docente(self):
        return self.rol == self.Rol.DOCENTE

    def __str__(self):
        return f"{self.email} ({self.get_rol_display()})"