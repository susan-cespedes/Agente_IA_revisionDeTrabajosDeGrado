from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.usuarios.services import guardar_token_google, obtener_o_crear_usuario

from .google_docs import ErrorGoogleDocs
from .services import extraer_id_documento, verificar_documento

ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789_-abcd"
KEY_PRUEBA = "sk-ant-api03-" + "x" * 40


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


class VerificarDocumentoTests(SimpleTestCase):

    @patch("apps.documentos.services.obtener_datos_basicos",
           return_value={"documentId": ID, "title": "Perfil"})
    def test_documento_nativo(self, _):
        self.assertEqual(verificar_documento(ID, "token"), "Perfil")

    def test_errores_de_google(self):
        casos = {400: "nativo", 401: "venció", 403: "permiso", 404: "No se encontró", 500: "no respondió"}
        for codigo, texto in casos.items():
            with self.subTest(codigo=codigo):
                with patch("apps.documentos.services.obtener_datos_basicos",
                           side_effect=ErrorGoogleDocs(codigo)):
                    with self.assertRaisesMessage(ValueError, texto):
                        verificar_documento(ID, "token")

    def test_sin_token(self):
        with self.assertRaisesMessage(ValueError, "venció"):
            verificar_documento(ID, None)


class VistaNuevaRevisionTests(TestCase):

    def setUp(self):
        self.client.force_login(obtener_o_crear_usuario("wilner.mena@ucb.edu.bo"))
        self.client.post(reverse("usuarios:api_key"), {"api_key": KEY_PRUEBA})
        guardar_token_google(self.client.session, "token-de-prueba", 3600)

    @patch("apps.documentos.services.obtener_datos_basicos",
           return_value={"documentId": ID, "title": "Perfil de prueba"})
    def test_muestra_titulo_e_id(self, _):
        r = self.client.post(reverse("documentos:nueva_revision"),
                             {"enlace": f"https://docs.google.com/document/d/{ID}/edit"})
        self.assertEqual(r.context["titulo"], "Perfil de prueba")
        self.assertContains(r, ID)

    @patch("apps.documentos.services.obtener_datos_basicos", side_effect=ErrorGoogleDocs(400))
    def test_rechaza_documento_no_nativo(self, _):
        r = self.client.post(reverse("documentos:nueva_revision"),
                             {"enlace": f"https://docs.google.com/document/d/{ID}/edit?usp=sharing"})
        self.assertIsNone(r.context["titulo"])
        self.assertContains(r, "no es un documento nativo")

    def test_muestra_error_de_enlace(self):
        r = self.client.post(reverse("documentos:nueva_revision"),
                             {"enlace": f"https://docs.google.com/spreadsheets/d/{ID}/edit"})
        self.assertIsNone(r.context["documento_id"])
        self.assertContains(r, "documento de texto")

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

    def test_requiere_sesion(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("documentos:nueva_revision")).status_code, 302)


class VistaSinTokenTests(TestCase):

    def setUp(self):
        self.client.force_login(obtener_o_crear_usuario("wilner.mena@ucb.edu.bo"))
        self.client.post(reverse("usuarios:api_key"), {"api_key": KEY_PRUEBA})

    def test_sin_token_pide_volver_a_ingresar(self):
        r = self.client.post(reverse("documentos:nueva_revision"),
                             {"enlace": f"https://docs.google.com/document/d/{ID}/edit"})
        self.assertContains(r, "venció")