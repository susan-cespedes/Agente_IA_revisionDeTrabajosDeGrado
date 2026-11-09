from django import forms


class ApiKeyForm(forms.Form):
    api_key = forms.CharField(
        label="API key de Anthropic",
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"placeholder": "sk-ant-...", "autocomplete": "off"},
        ),
        strip=True,
    )