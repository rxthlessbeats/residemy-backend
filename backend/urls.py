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
    path('api/upload_document/', views.upload_document, name='upload_document'),
    path('api/list_documents/', views.list_documents, name='list_documents'),
    path('api/update_document/', views.update_document, name='update_document'),
    path('api/delete_document/', views.delete_document, name='delete_document'),
    path('api/store_research_in_db/', views.store_research_in_db, name='store_research'),
    path('api/display_research_paper_table/', views.display_research_paper_table, name='display_research_paper_table'),
    path('api/display_documents/', views.display_documents, name='display_documents'),
    path('api/process_meta_item/', views.process_meta_item, name='process_meta_item'),
    path('api/extract_text_from_video/', views.extract_text_from_video, name='extract_text_from_video'),
    path('api/upload_user_document/', views.upload_user_document, name='upload_user_document'),
    path('api/list_user_documents/', views.list_user_documents, name='list_user_documents'),

    # openai 
    path('api/ask_question_about_image/', openai_views.ask_question_about_image, name='ask_question_about_image'),
    path('api/get_embedding/', openai_views.get_embedding, name='get_embedding'),
    path('api/generate_description/', openai_views.generate_description, name='generate_description'),
    path('api/generate_response/', openai_views.generate_response, name='generate_response'),

    path('accounts/', include('allauth.urls')),
    path('cms/', include('cms.urls')),  # Include Django CMS URLs
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) \
+ static(settings.USERDBS_URL, document_root=settings.USERDBS_ROOT)

