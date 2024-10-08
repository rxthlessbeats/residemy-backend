from django.contrib import admin
from django.urls import path, include
from . import views, openai_views, agent_views

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
    path('api/store_knowledge_in_db/', views.store_knowledge_in_db, name='store_knowledge'),
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
    path('api/generate_response_rag/', openai_views.generate_response_rag, name='generate_response_rag'),
    path('api/generate_response/', openai_views.generate_response, name='generate_response'),
    path('api/json-completer/', openai_views.json_completer, name='json_completer'),

    #agent
    path('api/simple_rag/', agent_views.simple_rag, name='simple_rag'),
    path('api/save-conversation/', agent_views.save_conversation, name='save_conversation'),
    path('api/get-last-conversation/<str:user_id>/', agent_views.get_last_conversation, name='get_last_conversation'),
    path('api/retrieve-conversations/<str:user_id>/<int:limit>/', agent_views.retrieve_conversations, name='retrieve_conversations'),

    path('api/insert-persona/', agent_views.insert_persona, name='insert_persona'),
    path('api/delete-persona/<str:persona_name>/', agent_views.delete_persona, name='delete_persona'),
    path('api/get-personas/<str:user_id>/', agent_views.get_personas, name='get_personas'),
    path('api/get-persona_by_name/<str:user_id>/<str:persona_name>/', agent_views.get_persona_by_name, name='get_persona_by_name'),

    path('api/insert-activity/', agent_views.insert_activity, name='insert_activity'),
    path('api/update-activity/', agent_views.update_activity, name='update_activity'),
    path('api/delete-activity/<str:user_id>/<int:activity_id>/', agent_views.delete_activity, name='delete_activity'),
    path('api/get-activities/<str:user_id>/', agent_views.get_activities, name='get_activities'),
    path('api/finish-activity/<str:user_id>/<int:activity_id>/', agent_views.finish_activity, name='finish_activity'),

    path('accounts/', include('allauth.urls')),
    path('cms/', include('cms.urls')),  # Include Django CMS URLs
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) \
+ static(settings.USERDBS_URL, document_root=settings.USERDBS_ROOT)

