from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    re_path(r"^assets/(?P<path>.*)$", serve, {"document_root": settings.BASE_DIR / "proposals/static/assets"}),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('proposals.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)