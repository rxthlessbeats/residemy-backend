# views.py
import requests
from django.shortcuts import redirect, render
from django.contrib.auth import login
from .models import User
from django.http import JsonResponse, HttpResponseRedirect
import os
from .models import Forum, ForumDocument
import openai

import textract
from dotenv import load_dotenv
from django.views.decorators.csrf import csrf_exempt
import json

load_dotenv(dotenv_path='.env.local', override=True)
openai.api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
LINE_CLIENT_ID = os.getenv("LINE_CLIENT_ID")
LINE_CLIENT_SECRET = os.getenv("LINE_CLIENT_SECRET")
LINE_REDIRECT_URI = os.getenv("BACKEND_URI") + "/api/line_callback"
BASE_URI = os.getenv("BASE_URI")


def line_login(request):
    line_auth_url = (
        f"https://access.line.me/oauth2/v2.1/authorize?response_type=code&client_id={LINE_CLIENT_ID}"
        f"&redirect_uri={LINE_REDIRECT_URI}&bot_prompt=aggressive&state=login&scope=profile%20openid%20email"
    )
    return redirect(line_auth_url)

@csrf_exempt
def line_callback(request):
    code = request.GET.get('code')
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': LINE_REDIRECT_URI,
        'client_id': LINE_CLIENT_ID,
        'client_secret': LINE_CLIENT_SECRET,
    }
    response = requests.post('https://api.line.me/oauth2/v2.1/token', data=data)
    token_json = response.json()

    # fetch email
    url = 'https://api.line.me/oauth2/v2.1/verify'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'id_token': token_json['id_token'],
        'client_id': LINE_CLIENT_ID,
    }
    response2 = requests.post(url, headers=headers, data=data)
    user_info2 = response2.json()
    # print(user_info2)
    
    # fetch status
    user_info_url = 'https://api.line.me/v2/profile'
    headers = {'Authorization': f'Bearer {token_json["access_token"]}'}
    user_info_response = requests.get(user_info_url, headers=headers)
    user_info = user_info_response.json()

    email = None
    status_message = None
    
    if 'email' in user_info2:
        email = user_info2['email']
    
    if 'statusMessage' in user_info:
        status_message = user_info['statusMessage']
    
    # Authenticate and log in the user
    user, created = User.objects.get_or_create(line_user_id=user_info['userId'])
    if created:
        # user.username = user_info['userId']
        user.display_name = user_info['displayName']
        user.profile_picture = user_info['pictureUrl']
        user.email = email
        user.status_message = status_message
        user.save()
    else:
        user.display_name = user_info['displayName']
        user.profile_picture = user_info['pictureUrl']
        user.email = email
        user.status_message = status_message
        user.save(update_fields=['display_name', 'profile_picture', 'email', 'status_message'])

    login(request, user)

    print(token_json['access_token'])
    print(token_json['id_token'])

    redirect_url = f"{BASE_URI}?access_token={token_json['access_token']}&id_token={token_json['id_token']}&user_id={user_info['userId']}"
    return HttpResponseRedirect(redirect_url)

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