from django.urls import path

from . import views

app_name = "documentos"

urlpatterns = [
    path("nueva/", views.nueva_revision, name="nueva_revision"),
]