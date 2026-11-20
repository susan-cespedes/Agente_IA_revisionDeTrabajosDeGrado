from django.urls import path

from . import views

app_name = "agente"

urlpatterns = [
    path("revisar/", views.revisar, name="revisar"),
    path("revision/<int:pk>/", views.detalle, name="detalle"),
]