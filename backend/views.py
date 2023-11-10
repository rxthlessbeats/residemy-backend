# views.py
from django.conf import settings
from django.contrib.auth import login
from django.shortcuts import redirect
import requests

def line_callback(request):
    code = request.GET.get('code')
    state = request.GET.get('state')

    # Optionally check the state value for CSRF protection

    # Exchange the code for a token
    response = requests.post('https://api.line.me/oauth2/v2.1/token', data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.LINE_REDIRECT_URI,
        'client_id': settings.LINE_CLIENT_ID,
        'client_secret': settings.LINE_CLIENT_SECRET,
    }, headers={
        'Content-Type': 'application/x-www-form-urlencoded'
    })

    response_data = response.json()

    if response.status_code == 200:
        access_token = response_data['access_token']

        # If you have a user model and want to log in the user:
        # user = authenticate(request, access_token=access_token) 
        # login(request, user)

        return redirect('/')
    else:
        # Handle error case
        return redirect('/404')
