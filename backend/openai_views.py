from dotenv import load_dotenv
load_dotenv(dotenv_path='.env.local', override=True)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import openai
import os
import logging

openai.api_key = os.getenv("OPENAI_API_KEY")

@csrf_exempt
@require_POST
def ask_question_about_image(request):
    try:
        data = json.loads(request.body)
        image_path = data.get("image_path")
        question = data.get("question")
        
        if not image_path or not question:
            return JsonResponse({"error": "image_path and question are required"}, status=400)
        
        client = openai.OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
        )
        
        completions = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_path,
                                "detail": "high"
                           },
                        },
                    ],
                }
            ],
            max_tokens=300,
        )
        response = completions.choices[0].message.content

        return JsonResponse({"response": response}, status=200)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return JsonResponse({"error": "An error occurred while processing the request"}, status=500)