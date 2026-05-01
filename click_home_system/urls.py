from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from proposals import ssq_views

urlpatterns = [
    re_path(r"^assets/(?P<path>.*)$", serve, {"document_root": settings.BASE_DIR / "proposals/static/assets"}),
    path("admin/login", ssq_views.admin_login, name="ssq_admin_login"),
    path("admin/logout", ssq_views.admin_logout, name="ssq_admin_logout"),
    path("admin/submissions", ssq_views.admin_submissions, name="ssq_admin_submissions"),
    path("admin/submissions/export/csv", ssq_views.admin_submissions_csv, name="ssq_admin_export_csv"),
    path("admin/submissions/<uuid:submission_id>", ssq_views.admin_submission_detail, name="ssq_admin_submission_detail"),
    path("admin/submissions/<uuid:submission_id>/export/pdf", ssq_views.admin_submission_pdf, name="ssq_admin_export_pdf"),
    path(
        "admin/submissions/<uuid:submission_id>/files/<str:file_key>/<int:index>",
        ssq_views.admin_submission_file,
        name="ssq_admin_file",
    ),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('proposals.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)