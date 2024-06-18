# views.py
import os
import json
import requests
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

from .models import User, Document
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from .utils import generate_pdf_thumbnail, generate_text_thumbnail, generate_video_thumbnail
from .openai_views import generate_summary

import base64
import cv2
from moviepy.editor import VideoFileClip

import tempfile
import openai
from pydub import AudioSegment
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_audio

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
        file_type = request.POST.get('file_type')
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
            'file_type': file_type,
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
            document.file_type = file_type
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

        elif file_type == 'videos':
            thumbnail = generate_video_thumbnail(doc_uri, doc_id)
            if thumbnail:
                document.thumbnail.save(thumbnail.name, thumbnail)
                document.save()

        return JsonResponse({'status': 'success', 'doc_id': document.doc_id}, status=200)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def list_documents(request):
    def fetch_documents(file_type, user_id=None, doc_id=None):
        if doc_id:
            document = get_object_or_404(Document, doc_id=doc_id)
            doc_list = [{
                f"{file_type} ID": document.doc_id,
                f"{file_type} Title": document.doc_title, 
                f"{file_type} URI": document.doc_uri,
                f"{file_type} Type": document.doc_type,
                f"{file_type} Description": document.doc_desc,
                f"{file_type} Text": document.doc_text,
                "File Type": document.file_type,
                "Create Date": document.doc_createdate,
                "Revise Date": document.doc_revisedate,
                "Display Date": document.display_date,
                "Expire Date": document.expire_date,
                "Share Flag": document.share_flag,
                "Audit Flag": document.audit_flag,
                f"{file_type} Meta": document.doc_meta,
                f"{file_type} Location": document.doc_loc,
                f"{file_type} MD5": document.doc_md5
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
                    f"{file_type} ID": doc.doc_id,
                    f"{file_type} Title": doc.doc_title,
                    f"{file_type} URI": doc.doc_uri,
                    f"{file_type} Type": doc.doc_type,
                    f"{file_type} Description": doc.doc_desc,
                    f"{file_type} Text": doc.doc_text,
                    "File Type": doc.file_type,
                    "Create Date": doc.doc_createdate,
                    "Revise Date": doc.doc_revisedate,
                    "Display Date": doc.display_date,
                    "Expire Date": doc.expire_date,
                    "Share Flag": doc.share_flag,
                    "Audit Flag": doc.audit_flag,
                    f"{file_type} Meta": doc.doc_meta,
                    f"{file_type} Location": doc.doc_loc,
                    f"{file_type} MD5": doc.doc_md5
                })
        
        return doc_list

    if request.method == 'POST':
        data = json.loads(request.body)
        user_id = data.get('user_id')
        doc_id = data.get('doc_id')
        file_type = data.get('file_type')
        documents = fetch_documents(file_type, user_id, doc_id)
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
        doc_meta = data.get('doc_meta')
        display_date = data.get('display_date')
        expire_date = data.get('expire_date')

        document = get_object_or_404(Document, doc_id=doc_id)
        if doc_title: document.doc_title = doc_title
        if doc_desc: document.doc_desc = doc_desc
        if doc_text: document.doc_text = doc_text
        if doc_meta: document.doc_meta = doc_meta
        if display_date: document.display_date = display_date
        if expire_date: document.expire_date = expire_date
        
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

class ResearchPaper(LanceModel):
        vector: Vector(1536) # type: ignore
        content: str
        doc_id: str
        user_id: str
        file_type: str
        page_id: int
    
        chunk_id: int
        start: float
        end: float

        display_date: int
        expire_date: int

@csrf_exempt
def store_research_in_db(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        json_data = data.get('json_data')
        user_id = data.get('user_id')
        doc_id = data.get('doc_id')
        file_type = data.get('file_type')
        display_date = datetime_to_timestamp(datetime.fromisoformat(data.get('display_date')))
        expire_date = datetime_to_timestamp(datetime.fromisoformat(data.get('expire_date')))

        # Connect to LanceDB
        vdb = lancedb.connect(LANCEDB_URI)

        # Convert JSON data to DataFrame
        df = json_to_dataframe(json_data, doc_id=doc_id, user_id=user_id, file_type=file_type)
        tbl_research = vdb.create_table("Research_paper_table", schema=ResearchPaper.to_arrow_schema(), exist_ok=True)
        print(df)
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
                'file_type': row['file_type'],
                'page_id': row['page'],
                
                'chunk_id': row['id'],
                'start': row['start'],
                'end': row['end'],

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

@csrf_exempt
def process_meta_item(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        video_path = data.get('video_path')
        meta_item = data.get('meta_item')
        doc_meta_tmp = data.get('doc_meta_tmp')
        languagestr = data.get('languagestr', 'en')

        base64Frames = []
        # base_video_path, _ = os.path.splitext(video_path)

        video = cv2.VideoCapture(video_path)
        fps = video.get(cv2.CAP_PROP_FPS)

        # Extract frames within the start and end times
        start_time = meta_item.get('start')
        end_time = meta_item.get('end')
        if start_time is not None and end_time is not None:
            for time_point in range(int(start_time), int(end_time), 2):
                frame_number = int(time_point * fps)
                video.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                success, frame = video.read()
                if success:
                    _, buffer = cv2.imencode(".jpg", frame)
                    base64Frames.append(base64.b64encode(buffer).decode("utf-8"))

        video.release()

        # Extract audio from video
        audio_path = f"{os.path.dirname(video_path)}/audios/{video_path.split('.')[0]}.mp3"
        clip = VideoFileClip(video_path)
        clip.audio.write_audiofile(audio_path, bitrate="32k")
        clip.audio.close()
        clip.close()

        # Generate summary
        transcript_data = "\n".join([item['text'] for item in doc_meta_tmp])
        extra_info = f"The abstract of this video is {meta_item['text']}."
        summary = generate_summary(base64Frames, transcript_data, extra_info, languagestr)

        meta_item['text'] = summary  # Update the summary in meta_item

        response_data = {
            'meta_item': meta_item,
            'base64Frames': base64Frames,
            'audio_path': audio_path
        }

        return JsonResponse(response_data, status=200)

    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def extract_text_from_video(request):
    if request.method == 'POST':
        try:
            video_content = request.FILES['file'].read()
            temp_dir = os.path.join(os.getcwd(), 'temp')
            os.makedirs(temp_dir, exist_ok=True)

            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4', dir=temp_dir) as temp_video_file:
                temp_video_file.write(video_content)
                temp_video_file_path = temp_video_file.name

            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3', dir=temp_dir) as temp_output_file:
                temp_output_file_name = temp_output_file.name

            if extract_audio(temp_video_file_path, temp_output_file_name):
                transcripts = extract_and_concatenate_segments(transcribe_audio(temp_output_file_name, temp_dir))

            os.remove(temp_video_file_path)
            os.remove(temp_output_file_name)

            print("transcripts:",transcripts)
            
            return JsonResponse({'status': 'success', 'transcripts': transcripts}, status=200)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

def extract_audio(input_file,output_file):
    file_extension = os.path.splitext(input_file)[1].lower()

    if file_extension in (".mp4", ".avi", ".mkv"):
        try:
            ffmpeg_extract_audio(input_file, output_file)
            print(f"Audio extracted from video and saved as {output_file}")
            return True
        except Exception as e:
            print(f"(ffmpeg_extract_audio) Error: {e}")
            return False
    elif file_extension in (".mp3", ".m4a",".wav"):
        print("Input file is already an audio file.")
        return False
    else:
        print("Unsupported file format.")
        return False
    
def transcribe_audio(file_path, temp_dir):
    CHUNK_SIZE_MB = 1
    CHUNK_SIZE_BYTES = int(CHUNK_SIZE_MB * 1024 * 1024 * 0.5)

    try:
        audio = AudioSegment.from_file(file_path)
        # print(f"len audio:{len(audio)}")
        # print(f"CHUNK_SIZE_BYTES:{(CHUNK_SIZE_BYTES)}")
    except Exception as e:
        # print(f"(transcribe_audio) An AudioSegmenterror occurred: {e}")
        return None

    chunks = [audio[i:i + CHUNK_SIZE_BYTES] for i in range(0, len(audio), CHUNK_SIZE_BYTES)]
    
    try:
        transcripts = []
        for i, chunk in enumerate(chunks):
            # print(i)
            fd, temp_audio_file = tempfile.mkstemp(suffix=".mp3", dir=temp_dir)
            os.close(fd)  # Close the file descriptor
            chunk.export(temp_audio_file, format="mp3")
            # print(i)
            with open(temp_audio_file, "rb") as audio_file:
                transcript = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )
                transcripts.append(transcript)

            os.remove(temp_audio_file)

    except Exception as e:
        print(f"(transcribe_audio) An error occurred: {e}")
        return None
    
    # print(f"transcripts: {transcripts}")
    
    return transcripts

def extract_and_concatenate_segments(transcripts):
    concatenated_segments = []
    max_id = 0
    last_end_time = 0.0

    for translation in transcripts:
        for segment in translation.segments:
            new_segment = {
                "id": max_id,
                "start": segment['start'],
                "end": segment['end'],
                "content": segment['text']
            }
            new_segment['start'] += last_end_time
            new_segment['end'] += last_end_time
            concatenated_segments.append(new_segment)
            max_id += 1
#            st.info(f"""new_segment(before):{new_segment}""")

        if translation.segments:
            last_end_time += translation.segments[-1]['end']
  
    return json.dumps(concatenated_segments, ensure_ascii=False, indent=4)