from django import forms


class EnlaceDocumentoForm(forms.Form):
    enlace = forms.CharField(
        label="Enlace del documento de Google Docs",
        widget=forms.URLInput(attrs={"placeholder": "https://docs.google.com/document/d/..."}),
        strip=True,
    )