from django import forms
from django.conf import settings

from .models import Revision


class RevisionForm(forms.Form):
    """Datos que el usuario elige antes de enviar el documento al agente."""

    documento_id = forms.CharField(widget=forms.HiddenInput)
    etapa = forms.ChoiceField(label="Etapa del trabajo de grado", choices=Revision.Etapa.choices,
                              initial=Revision.Etapa.PERFIL)
    modalidad = forms.ChoiceField(label="Modalidad", choices=Revision.Modalidad.choices,
                                  initial=Revision.Modalidad.PROYECTO_GRADO)
    modelo = forms.ChoiceField(label="Modelo de lenguaje")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # La lista de modelos sale de settings.py, para no repetirla en el código.
        self.fields["modelo"].choices = [(clave, datos["nombre"]) for clave, datos in settings.MODELOS_AGENTE.items()]
        self.fields["modelo"].initial = settings.MODELO_POR_DEFECTO