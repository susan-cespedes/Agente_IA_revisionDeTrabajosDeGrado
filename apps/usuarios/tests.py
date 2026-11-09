from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.cache import caches
from django.test import TestCase
from django.urls import reverse
from .models import Usuario
from .services import (
    borrar_api_key, es_correo_institucional, formato_api_key_valido, guardar_api_key,
    obtener_api_key, obtener_o_crear_usuario, rol_segun_correo, tiene_api_key,
)

KEY_PRUEBA = "sk-ant-api03-" + "x" * 40  # key falsa, solo para pruebas


class ServicioUsuariosTests(TestCase):

    def test_acepta_correo_de_la_ucb(self):
        self.assertTrue(es_correo_institucional("ccanedo@ucb.edu.bo"))

    def test_rechaza_correo_personal(self):
        self.assertFalse(es_correo_institucional("alguien@gmail.com"))

    def test_identifica_docentes(self):
        for correo in ["ccanedo@ucb.edu.bo", "lrodriguez.g@ucb.edu.bo", "narinez@ucb.edu.bo"]:
            with self.subTest(correo=correo):
                self.assertEqual(rol_segun_correo(correo), Usuario.Rol.DOCENTE)

    def test_identifica_estudiantes(self):
        for correo in ["wilner.mena@ucb.edu.bo", "susan.cespedez@ucb.edu.bo"]:
            with self.subTest(correo=correo):
                self.assertEqual(rol_segun_correo(correo), Usuario.Rol.ESTUDIANTE)

    def test_mayusculas_no_cambian_el_rol(self):
        self.assertEqual(rol_segun_correo("CCanedo@UCB.edu.bo"), Usuario.Rol.DOCENTE)

    def test_crea_usuario_la_primera_vez_y_lo_reutiliza(self):
        u1 = obtener_o_crear_usuario("narinez@ucb.edu.bo", "N.", "Arinez")
        u2 = obtener_o_crear_usuario("narinez@ucb.edu.bo")
        self.assertEqual(u1.pk, u2.pk)
        self.assertTrue(u1.es_docente)
        self.assertFalse(u1.has_usable_password())

    def test_no_crea_usuario_con_correo_personal(self):
        with self.assertRaises(PermissionError):
            obtener_o_crear_usuario("alguien@gmail.com")

class ServicioApiKeyTests(TestCase):

    def setUp(self):
        caches["api_keys"].clear()
        self.sesion = SessionStore()
        self.sesion.create()

    def test_formato_valido(self):
        self.assertTrue(formato_api_key_valido(KEY_PRUEBA))

    def test_formato_invalido(self):
        for key in ["", "hola", "sk-proj-123", "sk-ant-corta"]:
            with self.subTest(key=key):
                self.assertFalse(formato_api_key_valido(key))

    def test_guarda_y_recupera_en_la_misma_sesion(self):
        guardar_api_key(self.sesion, KEY_PRUEBA)
        self.assertEqual(obtener_api_key(self.sesion), KEY_PRUEBA)
        self.assertTrue(tiene_api_key(self.sesion))

    def test_otra_sesion_no_ve_la_key(self):
        guardar_api_key(self.sesion, KEY_PRUEBA)
        otra = SessionStore()
        otra.create()
        self.assertIsNone(obtener_api_key(otra))

    def test_borrar_la_key(self):
        guardar_api_key(self.sesion, KEY_PRUEBA)
        borrar_api_key(self.sesion)
        self.assertFalse(tiene_api_key(self.sesion))

    def test_rechaza_formato_invalido(self):
        with self.assertRaises(ValueError):
            guardar_api_key(self.sesion, "clave-cualquiera")

    def test_la_key_no_se_guarda_en_la_base_de_datos(self):
        guardar_api_key(self.sesion, KEY_PRUEBA)
        for s in Session.objects.all():
            self.assertNotIn(KEY_PRUEBA, s.session_data)

class VistasApiKeyTests(TestCase):

    def setUp(self):
        caches["api_keys"].clear()
        usuario = obtener_o_crear_usuario("wilner.mena@ucb.edu.bo")
        self.client.force_login(usuario)

    def test_registra_key_valida(self):
        r = self.client.post(reverse("usuarios:api_key"), {"api_key": KEY_PRUEBA}, follow=True)
        self.assertRedirects(r, reverse("usuarios:panel"))
        self.assertTrue(r.context["tiene_api_key"])
        self.assertNotContains(r, KEY_PRUEBA)

    def test_rechaza_key_invalida_sin_devolverla(self):
        r = self.client.post(reverse("usuarios:api_key"), {"api_key": "clave-cualquiera"})
        self.assertContains(r, "formato")
        self.assertNotContains(r, "clave-cualquiera")

    def test_salir_borra_la_key(self):
        self.client.post(reverse("usuarios:api_key"), {"api_key": KEY_PRUEBA})
        sesion = self.client.session.session_key
        self.client.post(reverse("usuarios:salir"))
        self.assertIsNone(caches["api_keys"].get(f"api_key:{sesion}"))

    def test_requiere_sesion_iniciada(self):
        self.client.logout()
        r = self.client.get(reverse("usuarios:api_key"))
        self.assertEqual(r.status_code, 302)