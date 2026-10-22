from pathlib import Path

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import FileResponse, Http404
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(('hotel.urls', 'hotel'), namespace='hotel')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


def favicon_view(request):
    """Віддає логотип на /favicon.ico — браузери запитують його автоматично."""
    icon = Path(settings.BASE_DIR) / 'hotel' / 'static' / 'hotel' / 'favicon.ico'
    if not icon.exists():
        raise Http404('favicon not found')
    return FileResponse(icon.open('rb'), content_type='image/x-icon')


urlpatterns.append(path('favicon.ico', favicon_view))
