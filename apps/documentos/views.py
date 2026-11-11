from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.usuarios.decorators import api_key_requerida
from apps.usuarios.services import obtener_token_google

from .forms import EnlaceDocumentoForm
from .services import extraer_id_documento, leer_documento


@login_required
@api_key_requerida
def nueva_revision(request):
    """Recibe el enlace, verifica y lee el documento, y muestra un resumen de lo leído."""
    documento = None
    if request.method == "POST":
        form = EnlaceDocumentoForm(request.POST)
        if form.is_valid():
            try:
                documento_id = extraer_id_documento(form.cleaned_data["enlace"])
                documento = leer_documento(documento_id, obtener_token_google(request.session))
            except ValueError as error:
                form.add_error("enlace", str(error))
    else:
        form = EnlaceDocumentoForm()
    return render(request, "documentos/nueva_revision.html", {"form": form, "documento": documento})