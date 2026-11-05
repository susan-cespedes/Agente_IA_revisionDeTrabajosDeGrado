from django.test import TestCase

from .models import Usuario
from .services import es_correo_institucional, obtener_o_crear_usuario, rol_segun_correo


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