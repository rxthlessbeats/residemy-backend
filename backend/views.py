# views.py
from django.conf import settings
from django.contrib.auth import login
from django.shortcuts import redirect
from django_nextjs.render import render_nextjs_page_sync
import requests

def index(request):
    return render_nextjs_page_sync(request)