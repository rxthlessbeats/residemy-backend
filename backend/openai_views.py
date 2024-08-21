from dotenv import load_dotenv
load_dotenv(dotenv_path='.env.local', override=True)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import openai
import os
import logging
from .utils import lang_detect, calculate_tokens
import lancedb

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
LANCEDB_URI = "master/lancedb/"

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

# from llama_index.core import VectorStoreIndex
# from llama_index.core.chat_engine import CondensePlusContextChatEngine
# from llama_index.core.indices.vector_store import VectorIndexRetriever
# from llama_index.core.memory import ChatMemoryBuffer
# from llama_index.llms.openai import OpenAI
# from llama_index.embeddings.openai import OpenAIEmbedding
# from llama_index.vector_stores.lancedb import LanceDBVectorStore

# def _get_memory(chat_store_key="foobar-default"):
#     return ChatMemoryBuffer.from_defaults(chat_store_key=chat_store_key)


# def _get_customized_llm(model="gpt-4o-2024-05-13"):
#     return OpenAI(model=model, temperature=0.0001)


# def _get_retriever(connection, table, text_key):
#     vector_store = LanceDBVectorStore(
#         connection=connection, 
#         table=table, 
#         text_key=text_key,
#         query_type="hybrid",
#     )

#     embed_model = OpenAIEmbedding(model="text-embedding-3-small")

#     index = VectorStoreIndex.from_vector_store(
#         vector_store=vector_store,
#         embed_model=embed_model
#     )

#     retriever = VectorIndexRetriever(
#         index=index,
#         similarity_top_k=3,
#     )

#     return retriever

@csrf_exempt
def generate_response(request):
    if request.method == 'POST':
        data = json.loads(request.body)  
        context = data.get('context', '')
        messages = data.get('messages', '')
        model = data.get('model', 'gpt-4o-2024-05-13')
        user_id = data.get('user_id', None)

        last_input = messages[-1]['content']
        db = lancedb.connect(f"{LANCEDB_URI}")
        tbl = db.open_table("Research_paper_table")

        # retriever = _get_retriever(db, tbl, "content")
        # llm = _get_customized_llm(model=model)
        # memory = _get_memory(f"{user_id}-conv")
        # chat_engine = CondensePlusContextChatEngine.from_defaults(
        #     retriever=retriever,
        #     llm=llm,
        #     memory=memory,
        #     system_prompt=context,
        # )

        # response_content = chat_engine.chat(f"{last_input}")
        # return JsonResponse({'response_content': response_content})

        # simple lancedb rag
        messages_embedding = client.embeddings.create(input = [last_input], model='text-embedding-3-small').data[0].embedding
    
        search_results = tbl.search(messages_embedding, vector_column_name='vector').limit(5).to_df()
        context_from_search = "\n".join(search_results['content'])

        messages_payload = [
            {"role": "system", "content": f"{context} and use the following context as reference to answer: {context_from_search}"},
            {"role": "user", "content": f"{messages}"},
        ]

        try:
            # Make a request to OpenAI using the Chat Completion endpoint
            completions = client.chat.completions.create(
                model=model,
                messages=messages_payload,
                temperature=0.0
            )

            # Extract the response content and the token usage
            response_content = completions.choices[0].message.content
            tokens_used = completions.usage.total_tokens

            ### TODO: update token used for user db###

            return JsonResponse({'response_content': response_content})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)

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