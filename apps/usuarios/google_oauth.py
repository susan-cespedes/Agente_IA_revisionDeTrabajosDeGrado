from authlib.integrations.django_client import OAuth
from django.conf import settings

oauth = OAuth()

# Permisos que se piden a Google (principio de mínimo privilegio: solo lectura).
PERMISOS_GOOGLE = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/drive.metadata.readonly",  # nombre y tipo del archivo
    "https://www.googleapis.com/auth/documents.readonly",       # contenido del documento
]

oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": " ".join(PERMISOS_GOOGLE)},
)

google = oauth.google