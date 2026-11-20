from django.contrib import admin

from .models import ObservacionRevision, Revision


class ObservacionInline(admin.TabularInline):
    model = ObservacionRevision
    extra = 0
    fields = ("orden", "severidad", "regla", "seccion", "fragmento", "descripcion", "fragmento_encontrado")


@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):
    list_display = ("nombre_documento", "usuario", "etapa", "modalidad", "modelo",
                    "tokens_entrada", "tokens_salida", "cantidad_observaciones", "simulado", "creada")
    list_filter = ("etapa", "modalidad", "modelo", "simulado")
    inlines = [ObservacionInline]