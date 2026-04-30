"""
URL configuration for Evalora project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from myapp.views import signup_disabled

urlpatterns = [
    path('admin/', admin.site.urls),

    # Public signup is DISABLED — redirect to login with a message
    # This must come BEFORE allauth.urls to intercept the signup route
    path('accounts/signup/', signup_disabled, name='account_signup'),

    # Authentication URLs (django-allauth) — login/logout only
    path('accounts/', include('allauth.urls')),

    # App URLs
    path('', include('myapp.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
