# views.py
import os
import json
import hashlib
from dotenv import load_dotenv
from .models import Forum, ForumDocument, User, Document

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

import openai
import textract


load_dotenv(dotenv_path='.env.local', override=True)
openai.api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

###################
# user table

@csrf_exempt
def update_user(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        line_user_id = data.get('user_id')
        display_name = data.get('user_displayName')
        profile_picture = data.get('user_pictureUrl')
        email = data.get('user_email')
        status_message = data.get('user_statusMessage')
        access_token = data.get('access_token')
        id_token = data.get('id_token')
        gpt_photo_desc = data.get('gpt_photo_desc')

        user, created = User.objects.get_or_create(line_user_id=line_user_id)
        gen_state = user.profile_picture != profile_picture or user.gpt_photo_desc == None
        print('gen_state:', gen_state)

        user.display_name = display_name
        user.profile_picture = profile_picture
        user.email = email
        user.status_message = status_message
        user.access_token = access_token
        user.id_token = id_token
        if gen_state:  # Only update gpt_photo_desc if we need to generate a new description
            user.gpt_photo_desc = gpt_photo_desc
        user.save()

        return JsonResponse({'status': 'success', 'gen_state': gen_state}, status=200)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def get_user_data(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_id = data.get('user_id')

        try:
            user = User.objects.get(line_user_id=user_id)
            user_data = {
                "user_id": user.line_user_id,
                "user_displayName": user.display_name,
                "user_pictureUrl": user.profile_picture,
                "user_statusMessage": user.status_message,
                "user_email": user.email,
                "access_token": user.access_token,
                "id_token": user.id_token,
                "gpt_photo_desc": user.gpt_photo_desc,
                "user_level": user.user_level
            }
            return JsonResponse(user_data, status=200)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)

    return JsonResponse({'error': 'Invalid request method'}, status=400)

########################
# document table

def calculate_md5(file_data):
    return hashlib.md5(file_data).hexdigest()

@csrf_exempt
def save_document(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_id = data.get('user_id')
        doc_title = data.get('doc_title')
        doc_desc = data.get('doc_desc')
        doc_type = data.get('doc_type')
        doc_md5 = data.get('doc_md5')
        doc_loc = data.get('doc_loc')
        doc_uri = data.get('doc_uri')
        doc_text = data.get('doc_text')
        display_date = data.get('display_date')
        expire_date = data.get('expire_date')

        user = get_object_or_404(User, line_user_id=user_id)

        doc_id = hashlib.md5((user_id + doc_title).encode()).hexdigest()

        document, created = Document.objects.get_or_create(doc_id=doc_id, defaults={
            'user': user,
            'doc_title': doc_title,
            'doc_desc': doc_desc,
            'doc_type': doc_type,
            'doc_md5': doc_md5,
            'doc_loc': doc_loc,
            'doc_uri': doc_uri,
            'doc_text': doc_text,
            'display_date': display_date,
            'expire_date': expire_date,
        })

        if not created:
            document.doc_title = doc_title
            document.doc_desc = doc_desc
            document.doc_type = doc_type
            document.doc_md5 = doc_md5
            document.doc_loc = doc_loc
            document.doc_uri = doc_uri
            document.doc_text = doc_text
            document.display_date = display_date
            document.expire_date = expire_date
            document.save()

        return JsonResponse({'status': 'success', 'doc_id': document.doc_id}, status=200)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def list_documents(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_id = data.get('user_id')

        user = get_object_or_404(User, line_user_id=user_id)
        documents = Document.objects.filter(user=user)

        doc_list = []
        for doc in documents:
            doc_list.append({
                'doc_id': doc.doc_id,
                'doc_title': doc.doc_title,
                'doc_desc': doc.doc_desc,
                'doc_type': doc.doc_type,
                'doc_md5': doc.doc_md5,
                'doc_loc': doc.doc_loc,
                'doc_uri': doc.doc_uri,
                'doc_text': doc.doc_text,
                'display_date': doc.display_date,
                'expire_date': doc.expire_date,
            })

        return JsonResponse({'status': 'success', 'documents': doc_list}, status=200)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def delete_document(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        doc_id = data.get('doc_id')
        user_id = data.get('user_id')

        user = get_object_or_404(User, line_user_id=user_id)
        document = get_object_or_404(Document, doc_id=doc_id, user=user)

        document.delete()

        return JsonResponse({'status': 'success'}, status=200)
    return JsonResponse({'error': 'Invalid request'}, status=400)

#########################

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

@csrf_exempt
def text_summarization(request):
    if request.method == 'POST':
        # Check if the request has a file in it
        if 'document' in request.FILES:
            document = request.FILES['document']
            # Assuming the document is a PDF or a TXT file
            text_to_summarize = textract.process(document.temporary_file_path()).decode('utf-8')
        else:
            # Load JSON data from request body if no file is present
            print("Received request body:", request.body)
            data = json.loads(request.body)
            text_to_summarize = data.get('text', None)

        if not text_to_summarize:
            return JsonResponse({'error': 'No text provided for summarization.'}, status=400)

        # Use OpenAI API to summarize the text
        response = client.chat.completions.create(model="gpt-4-turbo",  # Ensure this is the correct model you have access to
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Summarize the following text: {text_to_summarize}"}
        ])

        # Extract the summary from the response
        summary = response.choices[0].message.content

        # Return the summary in a JsonResponse
        return JsonResponse({'summary': summary})

    return JsonResponse({'error': 'This endpoint only supports POST requests.'}, status=405)