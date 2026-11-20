from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.documentos.services import leer_documento
from apps.usuarios.decorators import api_key_requerida
from apps.usuarios.services import obtener_api_key, obtener_token_google

from .forms import RevisionForm
from .models import Revision
from .proveedores import ErrorProveedor
from .services import guardar_revision, revisar_documento


@require_POST
@login_required
@api_key_requerida
def revisar(request):
    """Vuelve a leer el documento, lo envía al agente, guarda el resultado y lleva a su detalle."""
    form = RevisionForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Elige la etapa, la modalidad y el modelo antes de revisar.")
        return redirect("documentos:nueva_revision")

    datos = form.cleaned_data
    try:
        documento = leer_documento(datos["documento_id"], obtener_token_google(request.session))
        resultado = revisar_documento(documento, datos["etapa"], datos["modalidad"], datos["modelo"],
                                      obtener_api_key(request.session))
    except (ValueError, ErrorProveedor) as error:
        messages.error(request, str(error))
        return redirect("documentos:nueva_revision")

    revision = guardar_revision(request.user, datos["documento_id"], documento.titulo,
                                datos["etapa"], datos["modalidad"], resultado)
    messages.success(request, "Revisión guardada en tu historial.")
    return redirect("agente:detalle", pk=revision.pk)


@login_required
def detalle(request, pk):
    """Muestra una revisión guardada. Cada usuario solo puede ver las suyas."""
    revision = get_object_or_404(Revision, pk=pk, usuario=request.user)
    return render(request, "agente/resultado.html", {"revision": revision})