"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from . import views

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    # path('', include('django_nextjs.urls')),
    # path('', views.index, name='index'),
    path('api/store_line_user/', views.store_line_user, name='store_line_user'),
    path('api/forum_list/', views.forum_list, name='forum_list'),
    path('api/forums/<uuid:forum_id>/documents/', views.forum_documents, name='forum_documents'),
    path('api/record-click', views.record_click, name='record_click'),
    path('api/forum-record-click', views.forum_record_click, name='forum_record_click'),

    # path('accounts/', include('accounts.urls')),  # Assuming the app is named 'accounts' and the file is 'urls.py'
    path('cms/', include('cms.urls')),  # Include Django CMS URLs

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

