# utils.py
import pandas as pd
import json
import langid
import tiktoken
import io
import fitz
import cv2
from PIL import Image, ImageDraw, ImageFont
from django.core.files.uploadedfile import InMemoryUploadedFile

def json_to_dataframe(json_data, doc_id, user_id, file_type):
    json_data = json.loads(json_data)
    records = []
    for item in json_data:
        records.append({
            'content': item.get('content', None),
            'doc_id': doc_id,
            'user_id': user_id,
            'file_type': file_type,

            #documents
            'page': item.get('page', None),

            #videos
            'id': item.get('id', None),
            'start': item.get('start', None),
            'end': item.get('end', None),
        })
    return pd.DataFrame(records)

def datetime_to_timestamp(dt):
    return int(round(dt.timestamp()))

def lang_detect(text):
    languagetype = langid.classify(text[0:200])
    if (languagetype[0] == 'zh'):
        mylang = 'zh-tw'
    else:
        mylang = languagetype[0]
    return mylang

def calculate_tokens(text, model_name):
    enc = tiktoken.encoding_for_model(model_name)
    return len(enc.encode(text))

def generate_text_thumbnail(text, doc_id):
    # Create an image for the text thumbnail
    img = Image.new('RGB', (300, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    # Draw the text on the image
    draw.text((10, 10), text, fill=(0, 0, 0), font=font)

    # Save the image to a BytesIO object
    thumbnail_io = io.BytesIO()
    img.save(thumbnail_io, format='PNG')
    thumbnail_io.seek(0)

    # Create an InMemoryUploadedFile
    thumbnail = InMemoryUploadedFile(
        thumbnail_io, None, f"{doc_id}_thumbnail.png", 'image/png', thumbnail_io.getbuffer().nbytes, None
    )

    return thumbnail

def generate_pdf_thumbnail(file, doc_id):
    # Logic to generate a thumbnail for a PDF file
    pdf_document = fitz.open(stream=file.read(), filetype='pdf')
    page = pdf_document.load_page(0)  # Get the first page
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Save the image to a BytesIO object
    thumbnail_io = io.BytesIO()
    img.save(thumbnail_io, format='PNG')
    thumbnail_io.seek(0)

    # Create an InMemoryUploadedFile
    thumbnail = InMemoryUploadedFile(
        thumbnail_io, None, f"{doc_id}_thumbnail.png", 'image/png', thumbnail_io.getbuffer().nbytes, None
    )

    return thumbnail

def generate_video_thumbnail(file_path, doc_id):
    # Create a VideoCapture object
    video = cv2.VideoCapture(file_path)

    # Read the first frame
    success, image = video.read()

    # Check if frame is read correctly
    if not success:
        return None

    # Convert the frame to RGB
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Convert the frame to a PIL image
    pil_image = Image.fromarray(image)

    # Save the thumbnail as a BytesIO object
    thumbnail_io = io.BytesIO()
    pil_image.save(thumbnail_io, format='PNG')

    # Create an InMemoryUploadedFile
    thumbnail = InMemoryUploadedFile(
        thumbnail_io, None, f"{doc_id}_thumbnail.png", 'image/png', thumbnail_io.getbuffer().nbytes, None
    )

    return thumbnail