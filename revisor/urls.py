from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="usuarios:ingreso")),
    path("usuarios/", include("apps.usuarios.urls")),
    path("documentos/", include("apps.documentos.urls")),
    path("admin/", admin.site.urls),
]