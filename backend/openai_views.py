from dotenv import load_dotenv
load_dotenv(dotenv_path='.env.local', override=True)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import openai
import os
import logging
import textract
from .utils import lang_detect, calculate_tokens

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@csrf_exempt
@require_POST
def ask_question_about_image(request):
    try:
        data = json.loads(request.body)
        image_path = data.get("image_path")
        question = data.get("question")
        
        if not image_path or not question:
            return JsonResponse({"error": "image_path and question are required"}, status=400)
        
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
    
@csrf_exempt
def get_embedding(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            text = data.get('text')
            model = data.get('model', 'text-embedding-3-small')

            embedding = client.embeddings.create(input = [text], model=model).data[0].embedding

            return JsonResponse({'embedding': embedding}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@csrf_exempt
def generate_description(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        text = data.get('text')
        AI_rules = data.get('AI_rules')
        model_name = data.get('model_name', 'gpt-3.5-turbo')
        max_tokens = data.get('max_tokens', 0)
        max_output_tokens = data.get('max_output_tokens', 500)
        lang_mode = data.get('lang_mode', 1)

        # Define the context window size for each model
        model_token_input_limits = {
            "gpt-3.5-turbo": 4096,
            "gpt-4": 8192,
            "gpt-4o": 128000,
            "gpt-4-turbo": 128000,
        }

        try:
            # Determine the language of the input text
            mylang = lang_detect(text[0:200])

            if lang_mode == 1:
                # Determine the language of the input text
                mylang = lang_detect(text[0:200])

                languagestr = f"Please output in {mylang}, your answer:"
            else:
                languagestr = ""

            prompt = f"\n\n{text}\n\n{languagestr}"

            # Calculate the number of tokens in the prompt
            prompt_tokens = calculate_tokens(prompt, model_name)

            # Define the maximum number of tokens for the model
            if max_tokens > 0:
                max_total_tokens = max_tokens
            else:
                max_total_tokens = model_token_input_limits[model_name] * 0.5

            max_output_tokens = max_output_tokens  # You can adjust this based on your needs
            max_input_tokens = max_total_tokens - max_output_tokens

            # If the prompt is too long, trim the input text
            if prompt_tokens > max_input_tokens:
                # Trim the text to fit within the input token limit
                trimmed_text = text[:max_input_tokens - calculate_tokens(f"\n\n\n\n{languagestr}", model_name)]
                trimmed_prompt = f"\n\n{trimmed_text}\n\n{languagestr}"
                prompt_tokens = calculate_tokens(trimmed_prompt, model_name)
                messages_payload = [
                    {"role": "system", "content": AI_rules},
                    {"role": "user", "content": trimmed_prompt}
                ]
            else:
                messages_payload = [
                    {"role": "system", "content": AI_rules},
                    {"role": "user", "content": prompt}
                ]

            complete_response = ""
            total_tokens_used = 0
            while True:
                # Prepare the message payload with system prompts
                completions = client.chat.completions.create(
                    model=model_name,
                    messages=messages_payload,
                    max_tokens=max_output_tokens,
                    temperature=0.0
                )

                # Extract the response content and the token usage
                response = completions.choices[0].message.content
                tokens_used = completions.usage.total_tokens

                try:
                    complete_response += response
                    total_tokens_used += tokens_used
                except Exception as e:
                    print(f"General error: {e}")
                    return None

                # Check if the response is complete or if we need to continue
                if completions.choices[0].finish_reason == "stop":
                    break

                if completions.choices[0].finish_reason == "length":
                    messages_payload.append({"role": "assistant", "content": response})
                    messages_payload.append({"role": "user", "content": "Please continue the output from the end of the word of the previous response"})
                else:
                    break

                # Adjust the remaining tokens to avoid exceeding the limit
                if total_tokens_used >= max_total_tokens:
                    print(f"total_tokens_used {total_tokens_used} >= max_model_tokens")
                    break

            # Extract the response content and the token usage
            # response_content = complete_response

            return JsonResponse({'description': complete_response}, status=200)
        except Exception as e:
            return JsonResponse({'error': f"An error occurred while generating the description: {e}"}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=400)

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

###############################
### openai functions
###############################
def generate_summary(base64Frames, transcript_data, extra_info="",languagestr="en"):
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"""You are generating a video summary. Create a summary of the provided video and its transcript.If frame is silde, please specify it's a slide and extract the text from it. Respond in Markdown. The output language is in {languagestr}"""},
            {"role": "user", "content": [
                "These are the frames from the video.",
                *map(lambda x: {"type": "image_url", "image_url": {"url": f'data:image/jpg;base64,{x}', "detail": "low"}}, base64Frames),
                {"type": "text", "text": f"The audio transcription is: {transcript_data}. {extra_info}"}
            ]}
        ],
        temperature=0,
    )
    return response.choices[0].message.content