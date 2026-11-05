from authlib.integrations.base_client import OAuthError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .google_oauth import google
from .services import obtener_o_crear_usuario


def ingreso(request):
    """Muestra la pantalla de ingreso."""
    if request.user.is_authenticated:
        return redirect("usuarios:panel")
    return render(request, "usuarios/ingreso.html")


def ingresar_con_google(request):
    """Envía al usuario a la página de inicio de sesión de Google."""
    redirect_uri = request.build_absolute_uri(reverse("usuarios:google_callback"))
    return google.authorize_redirect(
        request,
        redirect_uri,
        hd=settings.DOMINIO_INSTITUCIONAL,  # Google sugiere solo cuentas de la UCB
        prompt="select_account",            # siempre deja elegir la cuenta
    )


def google_callback(request):
    """Google devuelve aquí al usuario después de iniciar sesión."""
    try:
        token = google.authorize_access_token(request)
    except OAuthError:
        messages.error(request, "No se pudo completar el ingreso con Google. Intenta de nuevo.")
        return redirect("usuarios:ingreso")

    datos = token.get("userinfo") or {}
    if not datos.get("email_verified"):
        messages.error(request, "Google no confirmó el correo de la cuenta.")
        return redirect("usuarios:ingreso")

    try:
        usuario = obtener_o_crear_usuario(
            datos["email"], datos.get("given_name", ""), datos.get("family_name", "")
        )
    except PermissionError as error:
        messages.error(request, str(error))
        return redirect("usuarios:ingreso")

    login(request, usuario)
    return redirect("usuarios:panel")


@require_POST
def salir(request):
    """Cierra la sesión."""
    logout(request)
    return redirect("usuarios:ingreso")


@login_required
def panel(request):
    """Página provisional después del ingreso: muestra quién es y su rol."""
    return render(request, "usuarios/panel.html")