from django.conf import settings
from django.db import models


class Revision(models.Model):
    """Una revisión hecha por el agente, con sus datos generales y sus observaciones.

    No guarda el documento completo: solo el resultado de la revisión.
    """

    class Etapa(models.TextChoices):
        PROPUESTA_TEMA = "PROPUESTA_TEMA", "Propuesta del tema"
        PERFIL = "PERFIL", "Perfil"
        DOCUMENTO_FINAL = "DOCUMENTO_FINAL", "Documento final (100%)"

    class Modalidad(models.TextChoices):
        PROYECTO_GRADO = "PROYECTO_GRADO", "Proyecto de grado"
        TRABAJO_DIRIGIDO = "TRABAJO_DIRIGIDO", "Trabajo dirigido"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="revisiones")
    documento_id = models.CharField("ID del documento", max_length=100)
    nombre_documento = models.CharField(max_length=255)
    etapa = models.CharField(max_length=20, choices=Etapa.choices)
    modalidad = models.CharField(max_length=20, choices=Modalidad.choices)
    modelo = models.CharField("modelo de lenguaje", max_length=60)
    tokens_entrada = models.PositiveIntegerField(default=0)
    tokens_salida = models.PositiveIntegerField(default=0)
    cantidad_observaciones = models.PositiveIntegerField(default=0)
    datos_generales = models.JSONField(default=dict)
    simulado = models.BooleanField(default=False)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creada"]
        verbose_name = "revisión"
        verbose_name_plural = "revisiones"

    def __str__(self):
        return f"{self.nombre_documento} – {self.get_etapa_display()} ({self.creada:%d/%m/%Y %H:%M})"

    @property
    def costo_estimado(self):
        precios = settings.MODELOS_AGENTE.get(self.modelo, {})
        return (self.tokens_entrada * precios.get("precio_entrada", 0)
                + self.tokens_salida * precios.get("precio_salida", 0)) / 1_000_000

    @property
    def conteo(self):
        return {s: self.observaciones.filter(severidad=s).count() for s in ObservacionRevision.Severidad.values}


class ObservacionRevision(models.Model):
    """Una observación del agente dentro de una revisión."""

    class Severidad(models.TextChoices):
        CRITICA = "CRITICA", "Crítica"
        MAYOR = "MAYOR", "Mayor"
        MENOR = "MENOR", "Menor"

    revision = models.ForeignKey(Revision, on_delete=models.CASCADE, related_name="observaciones")
    orden = models.PositiveIntegerField(default=0)
    seccion = models.CharField(max_length=255)
    regla = models.CharField(max_length=20)
    fragmento = models.TextField(blank=True)
    descripcion = models.TextField()
    severidad = models.CharField(max_length=10, choices=Severidad.choices)
    fragmento_encontrado = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden"]
        verbose_name = "observación"
        verbose_name_plural = "observaciones"

    def __str__(self):
        return f"{self.regla} ({self.get_severidad_display()}) – {self.seccion}"