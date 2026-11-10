from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .forms import EnlaceDocumentoForm
from .services import extraer_id_documento
from apps.usuarios.decorators import api_key_requerida

@login_required
@api_key_requerida
def nueva_revision(request):
    """Recibe el enlace del documento y muestra su ID o el error."""
    documento_id = None
    if request.method == "POST":
        form = EnlaceDocumentoForm(request.POST)
        if form.is_valid():
            try:
                documento_id = extraer_id_documento(form.cleaned_data["enlace"])
            except ValueError as error:
                form.add_error("enlace", str(error))
    else:
        form = EnlaceDocumentoForm()
    return render(request, "documentos/nueva_revision.html", {
        "form": form,
        "documento_id": documento_id,
    })

