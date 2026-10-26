"""
URL configuration for config project.
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from mainapp.views import dashboard_view
from mainapp import panel

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path('api/v1/', include('mainapp.urls')),
    # Akkauntlar haqida ma'lumot (faqat is_staff uchun)
    path(settings.PANEL_URL, panel.accounts_view, name='panel-accounts'),
    path(f'{settings.PANEL_URL}accounts/<int:pk>/', panel.account_detail_view, name='panel-account'),
    # Yordam: foydalanuvchilar xabarlari va javoblar
    path(f'{settings.PANEL_URL}support/', panel.support_inbox_view, name='panel-support'),
    path(f'{settings.PANEL_URL}support/<int:pk>/', panel.support_thread_view, name='panel-support-thread'),
    path(f'{settings.PANEL_URL}support/<int:pk>/poll/', panel.support_thread_poll_view, name='panel-support-poll'),
    # Admin xabarlari: bitta foydalanuvchiga yoki hammaga
    path(f'{settings.PANEL_URL}notices/', panel.notices_view, name='panel-notices'),
    path(f'{settings.PANEL_URL}notices/<int:pk>/delete/', panel.notice_delete_view, name='panel-notice-delete'),
    path('', dashboard_view, name='dashboard'),
]
