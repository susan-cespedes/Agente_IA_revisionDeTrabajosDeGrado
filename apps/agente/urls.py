from django.urls import path

from . import views

app_name = "agente"

urlpatterns = [
    path("revisar/", views.revisar, name="revisar"),
    path("historial/", views.historial, name="historial"),
    path("revision/<int:pk>/", views.detalle, name="detalle"),
    path("revision/<int:pk>/pdf/", views.descargar_pdf, name="pdf"),
]