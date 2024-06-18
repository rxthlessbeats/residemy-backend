from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone

class User(AbstractUser):
    line_user_id = models.CharField(max_length=255, unique=True, null=False, blank=False)
    profile_picture = models.URLField(max_length=200, blank=True, null=True)
    display_name = models.CharField(max_length=255, blank=True, null=True)
    status_message = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    access_token = models.CharField(max_length=1000, blank=True, null=True)  
    id_token = models.CharField(max_length=1000, blank=True, null=True)      
    gpt_photo_desc = models.TextField(blank=True, null=True) 
    user_level = models.IntegerField(blank=True, null=True, default=0)

    date_joined = models.DateTimeField(default=timezone.now)
    
    groups = models.ManyToManyField(Group, related_name='custom_user_set')
    user_permissions = models.ManyToManyField(Permission, related_name='custom_user_set_permissions')

    def __str__(self):
        return self.line_user_id
    
def documents_upload_uri(instance, filename):
    return f'{instance.file_type}/{instance.doc_id}.{instance.doc_type}'
    
def image_upload_uri(instance, filename):
    return f'{instance.file_type}/thumbnails/{instance.doc_id}_thumbnail.png'

class Document(models.Model):
    doc_id = models.CharField(max_length=1000, editable=False, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    doc_type = models.CharField(max_length=10)
    doc_loc = models.CharField(max_length=255)
    doc_uri = models.CharField(max_length=255)
    doc_title = models.CharField(max_length=255)
    doc_desc = models.TextField()
    doc_md5 = models.CharField(max_length=255)
    doc_text = models.TextField(blank=True, null=True)
    doc_meta = models.TextField(blank=True, null=True)
    file_type = models.CharField(max_length=255, blank=True, null=True)
    share_flag = models.BooleanField(default=False)
    audit_flag = models.BooleanField(default=False)
    display_date = models.DateTimeField(null=True, blank=True)
    expire_date = models.DateTimeField(null=True, blank=True)
    doc_createdate = models.DateTimeField(auto_now_add=True)
    doc_revisedate = models.DateTimeField(auto_now=True)
    file = models.FileField(upload_to=documents_upload_uri, null=True)
    thumbnail = models.ImageField(upload_to=image_upload_uri, blank=True, null=True)

    def __str__(self):
        return self.doc_title