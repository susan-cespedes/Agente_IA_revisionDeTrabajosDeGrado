from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.usuarios.services import guardar_token_google, obtener_o_crear_usuario

from .google_api import ErrorGoogle, obtener_metadatos
from .lector import leer_estructura
from .services import extraer_id_documento, leer_documento, verificar_documento

ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789_-abcd"
NATIVO = {"id": ID, "name": "Perfil", "mimeType": "application/vnd.google-apps.document"}
WORD = {"id": ID, "name": "Perfil.docx",
        "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
KEY_PRUEBA = "sk-ant-api03-" + "x" * 40


def parrafo(texto, estilo="NORMAL_TEXT", vineta=False):
    """Arma un párrafo con la misma forma que lo entrega Google Docs."""
    p = {"elements": [{"textRun": {"content": texto + "\n"}}], "paragraphStyle": {"namedStyleType": estilo}}
    if vineta:
        p["bullet"] = {"listId": "lista1"}
    return {"paragraph": p}


DOCUMENTO_JSON = {
    "title": "Perfil",
    "body": {"content": [
        {"sectionBreak": {}},
        parrafo("INTRODUCCIÓN", "HEADING_1"),
        parrafo("El presente trabajo aborda la revisión."),
        parrafo("1.1. Antecedentes Organizacionales", "HEADING_2"),
        parrafo("Primer punto", vineta=True),
        {"paragraph": {"elements": [{"inlineObjectElement": {"inlineObjectId": "img1"}}],
                       "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"}}},
        {"table": {"tableRows": [
            {"tableCells": [{"content": [parrafo("Rol")]}, {"content": [parrafo("Cantidad")]}]},
            {"tableCells": [{"content": [parrafo("Docente")]}, {"content": [parrafo("3")]}]},
        ]}},
        parrafo(""),
    ]},
}


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
        with self.assertRaisesMessage(ValueError, "Solo se permiten documentos nativos"):
            extraer_id_documento(enlace)

    def test_rechaza_enlace_sin_id(self):
        with self.assertRaises(ValueError):
            extraer_id_documento("https://docs.google.com/document/u/0/")


class VerificarDocumentoTests(SimpleTestCase):

    @patch("apps.documentos.services.obtener_metadatos", return_value=NATIVO)
    def test_documento_nativo(self, _):
        self.assertEqual(verificar_documento(ID, "token"), "Perfil")

    @patch("apps.documentos.services.obtener_metadatos", return_value=WORD)
    def test_rechaza_word_en_drive(self, _):
        with self.assertRaisesMessage(ValueError, "Solo se permiten documentos nativos"):
            verificar_documento(ID, "token")

    def test_errores_de_google(self):
        casos = {401: "venció", 403: "permiso", 404: "No se encontró", 500: "no respondió"}
        for codigo, texto in casos.items():
            with self.subTest(codigo=codigo):
                with patch("apps.documentos.services.obtener_metadatos",
                           side_effect=ErrorGoogle(codigo)):
                    with self.assertRaisesMessage(ValueError, texto):
                        verificar_documento(ID, "token")

    def test_razones_de_403(self):
        casos = {"SERVICE_DISABLED": "no está habilitada", "ACCESS_TOKEN_SCOPE_INSUFFICIENT": "No diste",
                 "insufficientPermissions": "No diste", "PERMISSION_DENIED": "No tienes permiso para abrir"}
        for razon, texto in casos.items():
            with self.subTest(razon=razon):
                with patch("apps.documentos.services.obtener_metadatos",
                           side_effect=ErrorGoogle(403, razon)):
                    with self.assertRaisesMessage(ValueError, texto):
                        verificar_documento(ID, "token")

    def test_sin_token(self):
        with self.assertRaisesMessage(ValueError, "venció"):
            verificar_documento(ID, None)


class RazonDelErrorTests(SimpleTestCase):

    def _respuesta(self, codigo, cuerpo):
        respuesta = Mock(status_code=codigo)
        respuesta.json.return_value = cuerpo
        return respuesta

    def test_lee_la_razon_de_google(self):
        cuerpo = {"error": {"code": 403, "status": "PERMISSION_DENIED",
                            "details": [{"@type": "type.googleapis.com/google.rpc.ErrorInfo",
                                         "reason": "SERVICE_DISABLED"}]}}
        with patch("apps.documentos.google_api.requests.get", return_value=self._respuesta(403, cuerpo)):
            with self.assertRaises(ErrorGoogle) as contexto:
                obtener_metadatos(ID, "token")
        self.assertEqual(contexto.exception.codigo, 403)
        self.assertEqual(contexto.exception.razon, "SERVICE_DISABLED")

    def test_lee_la_razon_del_formato_de_drive(self):
        cuerpo = {"error": {"code": 403, "errors": [{"reason": "insufficientPermissions"}]}}
        with patch("apps.documentos.google_api.requests.get", return_value=self._respuesta(403, cuerpo)):
            with self.assertRaises(ErrorGoogle) as contexto:
                obtener_metadatos(ID, "token")
        self.assertEqual(contexto.exception.razon, "insufficientPermissions")

    def test_sin_detalles_usa_el_estado(self):
        cuerpo = {"error": {"code": 403, "status": "PERMISSION_DENIED"}}
        with patch("apps.documentos.google_api.requests.get", return_value=self._respuesta(403, cuerpo)):
            with self.assertRaises(ErrorGoogle) as contexto:
                obtener_metadatos(ID, "token")
        self.assertEqual(contexto.exception.razon, "PERMISSION_DENIED")


class LectorTests(SimpleTestCase):

    def setUp(self):
        self.doc = leer_estructura(DOCUMENTO_JSON)

    def test_detecta_secciones_con_su_nivel(self):
        self.assertEqual([(x.nivel, x.titulo) for x in self.doc.secciones],
                         [(1, "INTRODUCCIÓN"), (2, "1.1. Antecedentes Organizacionales")])

    def test_marca_titulos_vinetas_y_tablas(self):
        self.assertIn("# INTRODUCCIÓN", self.doc.texto)
        self.assertIn("## 1.1. Antecedentes Organizacionales", self.doc.texto)
        self.assertIn("- Primer punto", self.doc.texto)
        self.assertIn("| Rol | Cantidad |", self.doc.texto)
        self.assertIn("| Docente | 3 |", self.doc.texto)

    def test_cuenta_tablas_imagenes_y_palabras(self):
        self.assertEqual(self.doc.tablas, 1)
        self.assertEqual(self.doc.imagenes, 1)
        self.assertEqual(self.doc.palabras, len(self.doc.texto.split()))
        self.assertEqual(self.doc.titulo, "Perfil")

    def test_documento_sin_titulos(self):
        doc = leer_estructura({"title": "X", "body": {"content": [parrafo("Solo texto normal")]}})
        self.assertEqual(doc.secciones, [])
        self.assertEqual(doc.texto, "Solo texto normal")

    def test_documento_vacio(self):
        doc = leer_estructura({"title": "Vacío"})
        self.assertEqual(doc.texto, "")
        self.assertEqual(doc.palabras, 0)


class LeerDocumentoTests(SimpleTestCase):

    @patch("apps.documentos.services.obtener_documento", return_value=DOCUMENTO_JSON)
    @patch("apps.documentos.services.obtener_metadatos", return_value=NATIVO)
    def test_lee_un_documento_nativo(self, _metadatos, _documento):
        doc = leer_documento(ID, "token")
        self.assertEqual(len(doc.secciones), 2)

    @patch("apps.documentos.services.obtener_documento")
    @patch("apps.documentos.services.obtener_metadatos", return_value=WORD)
    def test_no_lee_un_word(self, _metadatos, obtener_documento):
        with self.assertRaisesMessage(ValueError, "Solo se permiten documentos nativos"):
            leer_documento(ID, "token")
        obtener_documento.assert_not_called()

    @patch("apps.documentos.services.obtener_documento", side_effect=ErrorGoogle(403, "SERVICE_DISABLED"))
    @patch("apps.documentos.services.obtener_metadatos", return_value=NATIVO)
    def test_error_al_leer_el_contenido(self, _metadatos, _documento):
        with self.assertRaisesMessage(ValueError, "no está habilitada"):
            leer_documento(ID, "token")


class VistaNuevaRevisionTests(TestCase):

    def setUp(self):
        self.client.force_login(obtener_o_crear_usuario("wilner.mena@ucb.edu.bo"))
        self.client.post(reverse("usuarios:api_key"), {"api_key": KEY_PRUEBA})
        guardar_token_google(self.client.session, "token-de-prueba", 3600)

    @patch("apps.documentos.services.obtener_documento", return_value=DOCUMENTO_JSON)
    @patch("apps.documentos.services.obtener_metadatos", return_value=NATIVO)
    def test_muestra_el_resumen_del_documento(self, _metadatos, _documento):
        r = self.client.post(reverse("documentos:nueva_revision"),
                             {"enlace": f"https://docs.google.com/document/d/{ID}/edit"})
        self.assertEqual(r.context["documento"].titulo, "Perfil")
        self.assertContains(r, "Secciones detectadas (2)")
        self.assertContains(r, "1.1. Antecedentes Organizacionales")

    @patch("apps.documentos.services.obtener_metadatos", return_value=WORD)
    def test_rechaza_documento_no_nativo(self, _):
        r = self.client.post(reverse("documentos:nueva_revision"),
                             {"enlace": f"https://docs.google.com/document/d/{ID}/edit?usp=sharing"})
        self.assertIsNone(r.context["documento"])
        self.assertContains(r, "Solo se permiten documentos nativos")

    def test_muestra_error_de_enlace(self):
        r = self.client.post(reverse("documentos:nueva_revision"),
                             {"enlace": f"https://docs.google.com/spreadsheets/d/{ID}/edit"})
        self.assertIsNone(r.context["documento"])
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