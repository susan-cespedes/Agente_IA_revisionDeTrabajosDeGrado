from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode

from .services import tiene_api_key


def api_key_requerida(vista):
    """Solo deja pasar a la vista si la sesión tiene una API key registrada."""
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not tiene_api_key(request.session):
            messages.warning(request, "Registra tu API key antes de iniciar una revisión.")
            destino = urlencode({"next": request.get_full_path()})
            return redirect(f"{reverse('usuarios:api_key')}?{destino}")
        return vista(request, *args, **kwargs)
    return envoltura