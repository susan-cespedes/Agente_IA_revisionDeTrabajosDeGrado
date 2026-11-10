from django.test import SimpleTestCase

from .services import extraer_id_documento
from django.test import TestCase
from django.urls import reverse

from apps.usuarios.services import obtener_o_crear_usuario

ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789_-abcd"


class ExtraerIdDocumentoTests(SimpleTestCase):

    def test_enlaces_validos(self):
        enlaces = [
            f"https://docs.google.com/document/d/{ID}/edit",
            f"https://docs.google.com/document/d/{ID}/edit?usp=sharing",
            f"https://docs.google.com/document/d/{ID}/edit#heading=h.abc123",
            f"https://docs.google.com/document/d/{ID}",
            f"https://docs.google.com/document/u/0/d/{ID}/edit",
            f"  https://docs.google.com/document/d/{ID}/edit  ",
        ]
        for enlace in enlaces:
            with self.subTest(enlace=enlace):
                self.assertEqual(extraer_id_documento(enlace), ID)

    def test_rechaza_otros_sitios(self):
        for enlace in ["", "hola", f"http://docs.google.com/document/d/{ID}/edit", f"https://example.com/document/d/{ID}"]:
            with self.subTest(enlace=enlace):
                with self.assertRaises(ValueError):
                    extraer_id_documento(enlace)

    def test_rechaza_hojas_y_presentaciones(self):
        for enlace in [f"https://docs.google.com/spreadsheets/d/{ID}/edit", f"https://docs.google.com/presentation/d/{ID}/edit"]:
            with self.subTest(enlace=enlace):
                with self.assertRaisesMessage(ValueError, "documento de texto"):
                    extraer_id_documento(enlace)

    def test_rechaza_archivo_de_word_en_drive(self):
        enlace = f"https://docs.google.com/document/d/{ID}/edit?usp=sharing&ouid=123&rtpof=true&sd=true"
        with self.assertRaisesMessage(ValueError, "Word"):
            extraer_id_documento(enlace)

    def test_rechaza_enlace_sin_id(self):
        with self.assertRaises(ValueError):
            extraer_id_documento("https://docs.google.com/document/u/0/")


KEY_PRUEBA = "sk-ant-api03-" + "x" * 40
class VistaNuevaRevisionTests(TestCase):

    def setUp(self):
        self.client.force_login(obtener_o_crear_usuario("wilner.mena@ucb.edu.bo"))
        self.client.post(reverse("usuarios:api_key"), {"api_key": KEY_PRUEBA})

    def test_muestra_el_id(self):
        r = self.client.post(reverse("documentos:nueva_revision"),
                             {"enlace": f"https://docs.google.com/document/d/{ID}/edit"})
        self.assertEqual(r.context["documento_id"], ID)
        self.assertContains(r, ID)

    def test_muestra_el_error(self):
        r = self.client.post(reverse("documentos:nueva_revision"),
                             {"enlace": f"https://docs.google.com/spreadsheets/d/{ID}/edit"})
        self.assertIsNone(r.context["documento_id"])
        self.assertContains(r, "documento de texto")

    def test_requiere_sesion(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("documentos:nueva_revision")).status_code, 302)
    def test_sin_api_key_redirige_al_registro(self):
        self.client.post(reverse("usuarios:quitar_api_key"))
        r = self.client.get(reverse("documentos:nueva_revision"))
        self.assertRedirects(r, reverse("usuarios:api_key") + "?next=/documentos/nueva/")

    def test_despues_de_registrar_vuelve_a_la_revision(self):
        self.client.post(reverse("usuarios:quitar_api_key"))
        r = self.client.post(reverse("usuarios:api_key") + "?next=/documentos/nueva/",
                             {"api_key": KEY_PRUEBA})
        self.assertRedirects(r, reverse("documentos:nueva_revision"))

    def test_next_externo_se_ignora(self):
        r = self.client.post(reverse("usuarios:api_key") + "?next=https://sitio-malicioso.com/",
                             {"api_key": KEY_PRUEBA})
        self.assertRedirects(r, reverse("usuarios:panel"), fetch_redirect_response=False)