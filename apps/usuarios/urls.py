from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [
    path("ingreso/", views.ingreso, name="ingreso"),
    path("google/", views.ingresar_con_google, name="ingresar_con_google"),
    path("google/callback/", views.google_callback, name="google_callback"),
    path("salir/", views.salir, name="salir"),
    path("panel/", views.panel, name="panel"),
    path("api-key/", views.registrar_api_key, name="api_key"),
    path("api-key/quitar/", views.quitar_api_key, name="quitar_api_key"),
]