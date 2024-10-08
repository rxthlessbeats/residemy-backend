import lancedb
import openai
import os
import json
from dotenv import load_dotenv

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import connections, transaction, migrations

from .views import KnowledgeObject, ResearchPaper, apply_migrations_to_user_db, user_database_connection
from .models import UserChatLog, AgentPersona, UserActivityList

load_dotenv(dotenv_path='.env.local', override=True)
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

#################RAG AGENT######################

@csrf_exempt
def simple_rag(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_id = data.get('user_id')
        table_name = data.get('table_name')
        query_texts = data.get('query_texts')
        search_string = data.get('search_string')
        n_results = data.get('n_results')

        try:
            # Connect to the user's database
            vdb = lancedb.connect(f'userdbs/{user_id}/lancedb')
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": f"Failed to connect to database. Reason: {str(e)}"
            }, status=500)

        try:
            if table_name == "KnowledgeObject_table":
                table = vdb.create_table(table_name, schema=KnowledgeObject.to_arrow_schema(), exist_ok=True)
            elif table_name == "Research_paper_table":
                table = vdb.create_table(table_name, schema=ResearchPaper.to_arrow_schema(), exist_ok=True)
            else:
                return JsonResponse({
                    "status": "error",
                    "message": f"Table name {table_name} is not recognized."
                }, status=400)
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": f"Failed to create or access table. Reason: {str(e)}"
            }, status=500)

        try:
            # Get embeddings for the query texts
            messages_embedding = client.embeddings.create(
                input=[query_texts], model='text-embedding-3-small'
            ).data[0].embedding
            
            if search_string:
                where_clause = f"({search_string})"
                query_results = table.search(messages_embedding)\
                    .where(where_clause, prefilter=True)\
                    .metric("cosine")\
                    .limit(n_results)\
                    .to_df()
            else:
                query_results = table.search(messages_embedding)\
                    .metric("cosine")\
                    .limit(n_results)\
                    .to_df()
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": f"Failed to query table. Reason: {str(e)}"
            }, status=500)

        try:
            # Format the results
            results = {
                "doc_id": query_results["doc_id"].tolist(),
                "documents": query_results["content"].tolist(),
                "distance": query_results["_distance"].tolist()
            }
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": f"Error processing query results. Reason: {str(e)}"
            }, status=500)

        # Return the results in a standardized JSON format
        return JsonResponse({
            "status": "success",
            "message": "Query executed successfully.",
            "data": results
        }, status=200)

    return JsonResponse({
        "status": "error",
        "message": "Invalid request method. Only POST is allowed."
    }, status=405)

#####################CONVERSATION MEM###################

@csrf_exempt  
def save_conversation(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            doc_id = data.get('doc_id')
            dialog_session_id = data.get('dialog_session_id')
            dialog_text = data.get('dialog_text')
            dialog_meta = data.get('dialog_meta')

            if not user_id or not dialog_session_id:
                return JsonResponse({"error": "user_id and dialog_session_id are required."}, status=400)
            
            db_name = user_database_connection(user_id)
            connection = connections[db_name]
            with connection.cursor() as cursor:
                cursor.execute('PRAGMA foreign_keys = OFF;')

            with transaction.atomic(using=db_name):
                apply_migrations_to_user_db(connection, db_name)

                # Check if the conversation already exists
                chat_log, created = UserChatLog.objects.using(db_name).get_or_create(
                    dialog_session_id=dialog_session_id,
                    defaults={
                        'user_id': user_id,
                        'doc_id': doc_id,
                        'dialog_text': dialog_text,
                        'dialog_meta': dialog_meta,
                        'create_time': timezone.now(),
                        'last_update_time': timezone.now(),
                    }
                )

                if not created:
                    # Update the existing conversation
                    chat_log.dialog_text = dialog_text if dialog_text else chat_log.dialog_text
                    chat_log.dialog_meta = dialog_meta if dialog_meta else chat_log.dialog_meta
                    chat_log.last_update_time = timezone.now()
                    chat_log.save()

                return JsonResponse({"message": "Conversation saved successfully."}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Only POST requests are allowed."}, status=405)

def get_last_conversation(request, user_id):
    if request.method == 'GET':

        db_name = user_database_connection(user_id)
        connection = connections[db_name]
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA foreign_keys = OFF;')

        with transaction.atomic(using=db_name):
            apply_migrations_to_user_db(connection, db_name)

            try:
                chat_log = UserChatLog.objects.using(db_name).order_by('-create_time').first()

                if chat_log:
                    response_data = {
                        'doc_id': chat_log.doc_id,
                        'create_time': chat_log.create_time,
                        'last_update_time': chat_log.last_update_time,
                        'dialog_session_id': chat_log.dialog_session_id,
                        'dialog_text': chat_log.dialog_text,
                        'dialog_meta': chat_log.dialog_meta
                    }
                    return JsonResponse(response_data, status=200)
                else:
                    return JsonResponse({"message": "No conversation found."}, status=201)

            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Only GET requests are allowed."}, status=405)


def retrieve_conversations(request, user_id, limit=3):
    if request.method == 'GET':

        db_name = user_database_connection(user_id)
        connection = connections[db_name]
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA foreign_keys = OFF;')

        with transaction.atomic(using=db_name):
            apply_migrations_to_user_db(connection, db_name)

            try:
                chat_logs = UserChatLog.objects.using(db_name).order_by('-create_time')[:limit]
                response_data = [
                    {
                        'doc_id': log.doc_id,
                        'create_time': log.create_time,
                        'last_update_time': log.last_update_time,
                        'dialog_session_id': log.dialog_session_id,
                        'dialog_text': log.dialog_text,
                        'dialog_meta': log.dialog_meta
                    } for log in chat_logs
                ]
                return JsonResponse(response_data, status=200, safe=False)

            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Only GET requests are allowed."}, status=405)
    
###################AGENT PERSONA###################

@csrf_exempt
def insert_persona(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_id = data.get('user_id')
        persona_name = data.get('persona_name')
        persona_data = json.dumps(data.get('persona_data'))

        db_name = user_database_connection(user_id)
        connection = connections[db_name]
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA foreign_keys = OFF;')

        with transaction.atomic(using=db_name):
            apply_migrations_to_user_db(connection, db_name)

            try:
                persona, created = AgentPersona.objects.using(db_name).update_or_create(
                    persona_name=persona_name,
                    defaults={'persona_data': persona_data}
                )

                return JsonResponse({"message": "Persona saved successfully."}, status=200)
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)

def delete_persona(request, user_id, persona_name):
    if request.method == 'DELETE':
        db_name = user_database_connection(user_id)
        connection = connections[db_name]
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA foreign_keys = OFF;')

        with transaction.atomic(using=db_name):
            apply_migrations_to_user_db(connection, db_name)

            try:
                persona = AgentPersona.objects.using(db_name).get(persona_name=persona_name)
                persona.delete()
                return JsonResponse({"message": "Persona deleted successfully."}, status=200)
            except AgentPersona.DoesNotExist:
                return JsonResponse({"error": "Persona not found."}, status=404)
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)

def get_personas(request, user_id):
    if request.method == 'GET':
        db_name = user_database_connection(user_id)
        connection = connections[db_name]
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA foreign_keys = OFF;')

        with transaction.atomic(using=db_name):
            apply_migrations_to_user_db(connection, db_name)

            try:
                personas = AgentPersona.objects.using(db_name).all()
                persona_list = {
                    persona.persona_name: json.loads(persona.persona_data)
                    for persona in personas
                }
                return JsonResponse(persona_list, status=200)
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)

def get_persona_by_name(request, user_id, persona_name):
    if request.method == 'GET':
        db_name = user_database_connection(user_id)
        connection = connections[db_name]
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA foreign_keys = OFF;')

        with transaction.atomic(using=db_name):
            apply_migrations_to_user_db(connection, db_name)
        
            try:
                persona = AgentPersona.objects.using(db_name).get(persona_name=persona_name)
                persona_data = json.loads(persona.persona_data)
                # print("persona_data:", persona_data)
                return JsonResponse(persona_data, safe=False, status=200)
            except AgentPersona.DoesNotExist:
                return JsonResponse({"error": "Persona not found."}, status=200)
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)
            
@csrf_exempt
def insert_activity(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_id = data.get('user_id')
        activity_desc = data.get('activity_desc')
        session_id = data.get('session_id')
        finish_date = data.get('finish_date', None)

        db_name = user_database_connection(user_id)
        connection = connections[db_name]
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA foreign_keys = OFF;')

        with transaction.atomic(using=db_name):
            apply_migrations_to_user_db(connection, db_name)

            try:
                # Use update_or_create to either update an existing record or create a new one
                activity, created = UserActivityList.objects.using(db_name).update_or_create(
                    user_id=user_id,
                    session_id=session_id,  # Use user_id and session_id as unique identifiers
                    defaults={
                        'activity_desc': activity_desc,
                        'finish_date': finish_date,
                        'create_date': timezone.now()  # Update this field in case of update
                    }
                )

                if created:
                    return JsonResponse({"message": "Activity created successfully."}, status=200)
                else:
                    return JsonResponse({"message": "Activity updated successfully."}, status=200)
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def update_activity(request):
    if request.method == 'PUT':       
        data = json.loads(request.body)
        user_id = data.get('user_id')

        db_name = user_database_connection(user_id)
        connection = connections[db_name]
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA foreign_keys = OFF;')

        with transaction.atomic(using=db_name):
            apply_migrations_to_user_db(connection, db_name)

            try:
                activity = UserActivityList.objects.using(db_name).get(activity_id=data['activity_id'])

                if 'check_flag' in data:
                    activity.check_flag = data['check_flag']
                if 'activity_desc' in data:
                    activity.activity_desc = data['activity_desc']
                if 'finish_date' in data:
                    activity.finish_date = data['finish_date']

                activity.save()
                return JsonResponse({"message": "Activity updated successfully."}, status=200)
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)

def delete_activity(request, user_id, activity_id):
    if request.method == 'DELETE':

        db_name = user_database_connection(user_id)
        connection = connections[db_name]
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA foreign_keys = OFF;')

        with transaction.atomic(using=db_name):
            apply_migrations_to_user_db(connection, db_name)

            try:
                activity = UserActivityList.objects.using(db_name).get(activity_id=activity_id)
                activity.delete()
                return JsonResponse({"message": "Activity deleted successfully."}, status=200)
            except UserActivityList.DoesNotExist:
                return JsonResponse({"error": "Activity not found."}, status=404)
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)

def get_activities(request, user_id):
    if request.method == 'GET':

        db_name = user_database_connection(user_id)
        connection = connections[db_name]
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA foreign_keys = OFF;')

        with transaction.atomic(using=db_name):
            apply_migrations_to_user_db(connection, db_name)

            try:
                since_date = request.GET.get('since', None)
                if since_date:
                    activities = UserActivityList.objects.using(db_name).filter(user_id=user_id, check_flag=0, create_date__gte=since_date)
                else:
                    activities = UserActivityList.objects.using(db_name).filter(user_id=user_id, check_flag=0)

                activity_list = [
                    {
                        'activity_id': activity.activity_id,
                        'activity_desc': activity.activity_desc,
                        'create_date': activity.create_date,
                        'session_id': activity.session_id
                    } for activity in activities
                ]
                return JsonResponse(activity_list, status=200, safe=False)
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def finish_activity(request, user_id, activity_id):
    if request.method == 'PUT':

        db_name = user_database_connection(user_id)
        connection = connections[db_name]
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA foreign_keys = OFF;')

        with transaction.atomic(using=db_name):
            apply_migrations_to_user_db(connection, db_name)

            try:
                activity = UserActivityList.objects.using(db_name).get(activity_id=activity_id)
                activity.check_flag = 1
                activity.finish_date = timezone.now()
                activity.save()
                return JsonResponse({"message": "Activity finished successfully."}, status=200)
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)
