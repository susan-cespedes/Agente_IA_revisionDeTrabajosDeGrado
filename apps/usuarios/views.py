from authlib.integrations.base_client import OAuthError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST

from .forms import ApiKeyForm
from .google_oauth import google
from .services import (
    borrar_api_key, borrar_token_google, guardar_api_key, guardar_token_google,
    obtener_o_crear_usuario, tiene_api_key,
)


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
    # Se guarda DESPUÉS de login, porque login cambia el identificador de la sesión.
    guardar_token_google(request.session, token["access_token"], token.get("expires_in", 3600))
    return redirect("usuarios:panel")


@require_POST
def salir(request):
    """Cierra la sesión y elimina la API key y el token de Google de la memoria."""
    borrar_api_key(request.session)
    borrar_token_google(request.session)
    logout(request)
    return redirect("usuarios:ingreso")


@login_required
def panel(request):
    """Página provisional después del ingreso: quién es, su rol y el estado de la API key."""
    return render(request, "usuarios/panel.html", {
        "tiene_api_key": tiene_api_key(request.session),
    })


@sensitive_post_parameters("api_key")
@login_required
def registrar_api_key(request):
    """Muestra el formulario y registra la API key para la sesión."""
    if request.method == "POST":
        form = ApiKeyForm(request.POST)
        if form.is_valid():
            try:
                guardar_api_key(request.session, form.cleaned_data["api_key"])
            except ValueError as error:
                form.add_error("api_key", str(error))
            else:
                messages.success(request, "API key registrada para esta sesión.")
                destino = request.GET.get("next", "")
                if url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()},
                                                   require_https=request.is_secure()):
                    return redirect(destino)
                return redirect("usuarios:panel")
    else:
        form = ApiKeyForm()
    return render(request, "usuarios/api_key.html", {"form": form})


@require_POST
@login_required
def quitar_api_key(request):
    """Permite al usuario eliminar su key antes de salir."""
    borrar_api_key(request.session)
    messages.info(request, "Se eliminó la API key de esta sesión.")
    return redirect("usuarios:panel")