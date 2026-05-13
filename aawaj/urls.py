"""
AAWAJ Project URL Configuration.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from complaints import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Page routes
    path('', views.home_view, name='home'),
    path('report/', views.report_view, name='report'),
    path('track/', views.track_view, name='track'),
    path('dashboard/', views.public_dashboard_view, name='public_dashboard'),
    path('moderation/', views.moderation_view, name='moderation'),
    path('government/', views.government_dashboard_view, name='government'),
    path('government/case/<int:complaint_id>/', views.government_case_detail_view, name='gov_case_detail'),
    path('government/analytics/', views.government_analytics_view, name='gov_analytics'),
    path('map/', views.map_view, name='map'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # API routes
    path('', include('complaints.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
