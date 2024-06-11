# views.py
import os
import json
import hashlib
import requests
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

from .models import User, Document
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from .utils import generate_pdf_thumbnail, generate_text_thumbnail

load_dotenv(dotenv_path='.env.local', override=True)
BACKEND_URI = os.getenv("BACKEND_URI")
LANCEDB_URI = 'master/lancedb/'

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
def upload_document(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        doc_id = request.POST.get('doc_id')
        doc_title = request.POST.get('doc_title')
        doc_desc = request.POST.get('doc_desc')
        doc_type = request.POST.get('doc_type')
        doc_md5 = request.POST.get('doc_md5')
        doc_loc = request.POST.get('doc_loc')
        doc_uri = request.POST.get('doc_uri')
        doc_text = request.POST.get('doc_text')
        display_date = request.POST.get('display_date')
        expire_date = request.POST.get('expire_date')
        file = request.FILES['file']

        user = get_object_or_404(User, line_user_id=user_id)

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
            'file': file,
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
            document.file.save(file.name, file)
            document.save()

        file.seek(0)
        # Generate and save the thumbnail
        if doc_type == 'pdf':
            # Generate thumbnail for PDF
            thumbnail = generate_pdf_thumbnail(file, doc_id)
            document.thumbnail.save(thumbnail.name, thumbnail)
            document.save()
        elif doc_type == 'txt':
            # Generate thumbnail for text file
            try:
                text_preview = doc_text[:500] 
            except:
                text_preview = doc_text[:]
            thumbnail = generate_text_thumbnail(text_preview, doc_id)
            document.thumbnail.save(thumbnail.name, thumbnail)
            document.save()

        return JsonResponse({'status': 'success', 'doc_id': document.doc_id}, status=200)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def list_documents(request):
    def fetch_documents(user_id=None, doc_id=None):
        if doc_id:
            document = get_object_or_404(Document, doc_id=doc_id)
            doc_list = [{
                "Document ID": document.doc_id,
                "Document Title": document.doc_title,
                "Document URI": document.doc_uri,
                "Document Type": document.doc_type,
                "Document Description": document.doc_desc,
                "Document Text": document.doc_text,
                "Document Create Date": document.doc_createdate,
                "Document Revise Date": document.doc_revisedate,
                "Display Date": document.display_date,
                "Expire Date": document.expire_date,
                "Share Flag": document.share_flag,
                "Audit Flag": document.audit_flag,
                "Document Meta": document.doc_meta,
                "Document Location": document.doc_loc,
                "Document MD5": document.doc_md5
            }]
        else:
            if user_id:
                user = get_object_or_404(User, line_user_id=user_id)
                documents = Document.objects.filter(user=user)
            else:
                documents = Document.objects.all()

            doc_list = []
            for doc in documents:
                doc_list.append({
                    "Document ID": doc.doc_id,
                    "Document Title": doc.doc_title,
                    "Document URI": doc.doc_uri,
                    "Document Type": doc.doc_type,
                    "Document Description": doc.doc_desc,
                    "Document Text": doc.doc_text,
                    "Document Create Date": doc.doc_createdate,
                    "Document Revise Date": doc.doc_revisedate,
                    "Display Date": doc.display_date,
                    "Expire Date": doc.expire_date,
                    "Share Flag": doc.share_flag,
                    "Audit Flag": doc.audit_flag,
                    "Document Meta": doc.doc_meta,
                    "Document Location": doc.doc_loc,
                    "Document MD5": doc.doc_md5
                })
        
        return doc_list

    if request.method == 'POST':
        data = json.loads(request.body)
        user_id = data.get('user_id')
        doc_id = data.get('doc_id')
        documents = fetch_documents(user_id, doc_id)
        return JsonResponse({'status': 'success', 'documents': documents}, status=200)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def update_document(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        doc_id = data.get('doc_id')
        doc_title = data.get('doc_title')
        doc_desc = data.get('doc_desc')
        doc_text = data.get('doc_text')
        display_date = data.get('display_date')
        expire_date = data.get('expire_date')

        document = get_object_or_404(Document, doc_id=doc_id)
        document.doc_title = doc_title
        document.doc_desc = doc_desc
        document.doc_text = doc_text
        if display_date:
            document.display_date = display_date
        if expire_date:
            document.expire_date = expire_date
        
        document.save()

        return JsonResponse({'status': 'success', 'message': 'Document updated successfully.'}, status=200)
    
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

        vdb = lancedb.connect(LANCEDB_URI)
        tbl_research = vdb.open_table("Research_paper_table")
        if tbl_research:
            tbl_research.delete(f"""doc_id = '{doc_id}'""")

        return JsonResponse({'status': 'success'}, status=200)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def display_documents(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        amount = data.get('amount', 3)

        try:
            # Get the current date and time
            current_datetime = datetime.now()

            # Retrieve three news items within display_date and expire_date
            documents = Document.objects.filter(
                (Q(display_date__isnull=True) | Q(display_date__lte=current_datetime)),
                (Q(expire_date__isnull=True) | Q(expire_date__gte=current_datetime))
            ).order_by('?')[:amount][:amount]

            if documents.exists():
                news_items = {}
                for doc in documents:
                    news_item = {
                        # "Document ID": doc.doc_id,
                        "Title": doc.doc_title,
                        "Description": doc.doc_desc
                    }
                    news_items[doc.doc_id] = news_item
                return JsonResponse({'status': 'success', 'news_items': news_items}, status=200)
            else:
                return JsonResponse({'status': 'success', 'news_items': {}}, status=200)

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


########################
import lancedb
from lancedb.pydantic import Vector, LanceModel
from .utils import datetime_to_timestamp, json_to_dataframe

class DocumentPage(LanceModel):
        vector: Vector(1536) # type: ignore
        content: str
        doc_id: str
        user_id: str
        page_id: int
        seg_id: int
        doc_type: str

class ResearchPaper(LanceModel):
        vector: Vector(1536) # type: ignore
        content: str
        doc_id: str
        user_id: str
        page_id: int
        display_date: int
        expire_date:int

@csrf_exempt
def store_research_in_db(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        json_data = data.get('json_data')
        user_id = data.get('user_id')
        doc_id = data.get('doc_id')
        display_date = datetime_to_timestamp(datetime.fromisoformat(data.get('display_date')))
        expire_date = datetime_to_timestamp(datetime.fromisoformat(data.get('expire_date')))

        # Connect to LanceDB
        vdb = lancedb.connect(LANCEDB_URI)

        # Convert JSON data to DataFrame
        df = json_to_dataframe(json_data, doc_id=doc_id, user_id=user_id)
        tbl_research = vdb.create_table("Research_paper_table", schema=ResearchPaper.to_arrow_schema(), exist_ok=True)

        # Prepare records
        records = []
        for _, row in df.iterrows():
            text = row['content']
            embedding_response = requests.post(
                f"{BACKEND_URI}/api/get_embedding/",
                json={'text': text}
            )
            embedding = embedding_response.json().get('embedding')
            records.append({
                'vector': embedding,
                'content': row['content'],
                'doc_id': row['doc_id'],
                'user_id': row['user_id'],
                'page_id': row['page'],
                'display_date': display_date,
                'expire_date': expire_date
            })

        records_df = pd.DataFrame(records)
        tbl_research.add(records_df)

        return JsonResponse({'status': 'success'}, status=200)
    return JsonResponse({'error': 'Invalid request method'}, status=400)

def display_research_paper_table(request):
    db = lancedb.connect("master/lancedb/")

    try:
        tbl_research = db.open_table("Research_paper_table")

        # Convert to DataFrame
        df = tbl_research.to_pandas()

        # Convert timestamps back to datetime
        if 'display_date' in df.columns:
            df['display_date'] = pd.to_datetime(df['display_date'], unit='s')
        if 'expire_date' in df.columns:
            df['expire_date'] = pd.to_datetime(df['expire_date'], unit='s')

        # Convert DataFrame to JSON
        data = df.to_json(orient='records', date_format='iso')

        return JsonResponse({'status': 'success', 'data': json.loads(data)}, status=200)

    except Exception as e:
        # logging.error(f"(display_research_paper_table) An error occurred while retrieving the research paper table: {e}")
        return JsonResponse({'status': 'error', 'message': f"(display_research_paper_table) An error occurred while retrieving the research paper table: {str(e)}"}, status=500)

#########################