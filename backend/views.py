# views.py
from django.conf import settings
from django_nextjs.render import render_nextjs_page_sync
from django.http import JsonResponse
from neo4j import GraphDatabase
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.decorators import api_view
from rest_framework.response import Response

def index(request):
    return render_nextjs_page_sync(request)

from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def store_line_user(request):
    # Parse request data
    # user_data = request.GET 

    user_data = json.loads(request.body)
    print(user_data)

    # Connect to Neo4j
    driver = GraphDatabase.driver("neo4j+ssc://51ebc70c.databases.neo4j.io", auth=('neo4j', 'F-gS2PQd_aVaEn7g5uS-fg-YFrBZ8GGc4eqS4GJatXU'))

    def create_user(tx, user_id, display_name, picture_url, email):
        tx.run("MERGE (u:User {userId: $user_id}) "
               "SET u.displayName = $display_name, u.pictureUrl = $picture_url, u.email = $email",
               user_id=user_id, display_name=display_name, picture_url=picture_url, email=email)

    # Write to Neo4j
    with driver.session(database='neo4j') as session:
        session.execute_write(create_user, user_data['userId'], user_data['displayName'], user_data['pictureUrl'], user_data['email'])

    driver.close()
    return JsonResponse({'status': 'success' ,'userId': user_data['userId']})