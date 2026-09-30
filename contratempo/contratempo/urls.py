"""
URL configuration for contratempo project.

As rotas do marketplace ficam em marketplace/urls.py.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('marketplace.urls')),
]

# Em desenvolvimento o próprio Django serve os uploads (MEDIA). Em
# produção quem serve /static/ e /media/ é o servidor web (no
# PythonAnywhere: aba Web > Static files — veja DEPLOY.md).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Handlers de erro — só são usados com DEBUG = False.
handler403 = "marketplace.views_errors.acesso_negado"
handler404 = "marketplace.views_errors.pagina_nao_encontrada"
handler500 = "marketplace.views_errors.erro_servidor"
