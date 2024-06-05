# utils.py
import pandas as pd
import json
import langid
import tiktoken
import io
import fitz
from PIL import Image, ImageDraw, ImageFont
from django.core.files.uploadedfile import InMemoryUploadedFile

def json_to_dataframe(json_data, doc_id, user_id):
    json_data = json.loads(json_data)
    records = []
    for item in json_data:
        records.append({
            'doc_id': doc_id,
            'user_id': user_id,
            'page': item['page'],
            'content': item['content'],
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