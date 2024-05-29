from django.contrib import admin
from django.urls import path, include
from . import views

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/line_login/', views.line_login, name='line_login'),
    path('api/line_callback/', views.line_callback, name='line_callback'),
    # path('api/store_line_user/', views.store_line_user, name='store_line_user'),
    path('api/forum_list/', views.forum_list, name='forum_list'),
    path('api/forums/<uuid:forum_id>/documents/', views.forum_documents, name='forum_documents'),
    path('api/record-click', views.record_click, name='record_click'),
    path('api/forum-record-click', views.forum_record_click, name='forum_record_click'),
    path('api/text_summarization/', views.text_summarization, name='text_summarization'),
    path('accounts/', include('allauth.urls')),
    path('cms/', include('cms.urls')),  # Include Django CMS URLs

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

