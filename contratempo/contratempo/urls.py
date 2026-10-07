from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('marketplace.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = "marketplace.views_errors.acesso_negado"
handler404 = "marketplace.views_errors.pagina_nao_encontrada"
handler500 = "marketplace.views_errors.erro_servidor"
