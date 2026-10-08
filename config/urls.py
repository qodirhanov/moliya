"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from mainapp.views import dashboard_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('mainapp.urls')),
    path('', dashboard_view, name='dashboard'),
]
