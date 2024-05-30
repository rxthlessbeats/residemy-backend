from django.contrib import admin
from django.urls import path, include
from . import views
from . import openai_views

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # user model
    path('api/update_user/', views.update_user, name='update_user'),
    path('api/get_user_data/', views.get_user_data, name='get_user_data'),

    # document model
    path('api/save_document/', views.save_document, name='save_document'),
    # path('api/list_documents/', views.list_documents, name='list_documents'),
    path('api/delete_document/', views.delete_document, name='delete_document'),

    path('api/forum_list/', views.forum_list, name='forum_list'),
    path('api/forums/<uuid:forum_id>/documents/', views.forum_documents, name='forum_documents'),
    path('api/record-click', views.record_click, name='record_click'),
    path('api/forum-record-click', views.forum_record_click, name='forum_record_click'),
    path('api/text_summarization/', views.text_summarization, name='text_summarization'),
    path('accounts/', include('allauth.urls')),
    path('cms/', include('cms.urls')),  # Include Django CMS URLs

    # openai 
    path('api/ask_question_about_image/', openai_views.ask_question_about_image, name='ask_question_about_image'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

