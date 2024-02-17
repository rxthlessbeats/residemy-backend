# views.py
from django.conf import settings
# from django_nextjs.render import render_nextjs_page_sync
from django.http import JsonResponse
from neo4j import GraphDatabase
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.decorators import api_view
from rest_framework.response import Response
import os
from .models import Forum, ForumDocument

# def index(request):
#     return render_nextjs_page_sync(request)

from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def store_line_user(request):
    # Parse request data
    # user_data = request.GET 

    user_data = json.loads(request.body)
    print(user_data)

    # Connect to Neo4j
    driver = GraphDatabase.driver("neo4j+ssc://51ebc70c.databases.neo4j.io", auth=('neo4j', 'F-gS2PQd_aVaEn7g5uS-fg-YFrBZ8GGc4eqS4GJatXU'))

    def create_user(tx, user_id, display_name, picture_url, email):
        tx.run("MERGE (u:User {userId: $user_id}) "
               "SET u.displayName = $display_name, u.pictureUrl = $picture_url, u.email = $email",
               user_id=user_id, display_name=display_name, picture_url=picture_url, email=email)

    # Write to Neo4j
    with driver.session(database='neo4j') as session:
        session.execute_write(create_user, user_data['userId'], user_data['displayName'], user_data['pictureUrl'], user_data['email'])

    driver.close()
    return JsonResponse({'status': 'success' ,'userId': user_data['userId']})

def forum_list(request):
    forums = Forum.objects.all()
    data = [
        {
            "id": forum.folderId,
            "title": forum.title,
            "description": forum.description,
            "logo_url": forum.get_logo_url(),
            "upload_time": forum.upload_time.strftime('%Y-%m-%d'),
            "click_count": forum.click_count,
        }
        for forum in forums
    ]
    return JsonResponse(data, safe=False)

def forum_documents(request, forum_id):
    try:
        # Retrieve the forum by its ID or handle the case where it doesn't exist
        forum = Forum.objects.get(pk=forum_id)
        documents = forum.forum_documents.all()
        data = [
            {
                "id": document.id,
                "title": document.title,
                "document_url": document.document.url,
                "snapshot_url": document.snapshot.url if document.snapshot else None,
                "upload_time": document.upload_time.strftime('%Y-%m-%d'),
                "click_count": document.click_count,
            }
            for document in documents
        ]
        return JsonResponse(data, safe=False)
    except Forum.DoesNotExist:
        return JsonResponse({'error': 'Forum not found'}, status=404)
    
@csrf_exempt
def record_click(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ppt_id = data.get('pptId')
        # Increment click count in the database
        ppt = ForumDocument.objects.get(id=ppt_id)
        ppt.click_count += 1
        ppt.save()
        
        return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'error'}, status=400)

@csrf_exempt
def forum_record_click(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        forum_id = data.get('forumId')
        # Increment click count in the database
        forum = Forum.objects.get(pk=forum_id)
        forum.click_count += 1
        forum.save()
        
        return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'error'}, status=400)