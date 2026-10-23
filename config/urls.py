from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, Http404
from django.urls import include, path, re_path
from django.views.static import serve as media_serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(('hotel.urls', 'hotel'), namespace='hotel')),
    # Медіа (фото номерів). static() із django.conf.urls.static працює лише
    # при DEBUG=True, а на Render DEBUG=False — тому маршрут завжди активний.
    re_path(
        r'^media/(?P<path>.*)$',
        media_serve,
        {'document_root': settings.MEDIA_ROOT},
    ),
]


def favicon_view(request):
    """Віддає логотип на /favicon.ico — браузери запитують його автоматично."""
    icon = Path(settings.BASE_DIR) / 'hotel' / 'static' / 'hotel' / 'favicon.ico'
    if not icon.exists():
        raise Http404('favicon not found')
    return FileResponse(icon.open('rb'), content_type='image/x-icon')


urlpatterns.append(path('favicon.ico', favicon_view))
