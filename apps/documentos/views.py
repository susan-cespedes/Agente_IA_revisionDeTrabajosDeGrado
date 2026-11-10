from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.usuarios.decorators import api_key_requerida
from apps.usuarios.services import obtener_token_google

from .forms import EnlaceDocumentoForm
from .services import extraer_id_documento, verificar_documento


@login_required
@api_key_requerida
def nueva_revision(request):
    """Recibe el enlace, lo verifica con Google y muestra el título o el error."""
    documento_id = None
    titulo = None
    if request.method == "POST":
        form = EnlaceDocumentoForm(request.POST)
        if form.is_valid():
            try:
                documento_id = extraer_id_documento(form.cleaned_data["enlace"])
                titulo = verificar_documento(documento_id, obtener_token_google(request.session))
            except ValueError as error:
                documento_id = None
                form.add_error("enlace", str(error))
    else:
        form = EnlaceDocumentoForm()
    return render(request, "documentos/nueva_revision.html", {
        "form": form,
        "documento_id": documento_id,
        "titulo": titulo,
    })