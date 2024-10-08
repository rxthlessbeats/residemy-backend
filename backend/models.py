from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone
import os 
from .custom_storage import UserDocumentStorage

###########################MASTER DATABASE###########################

class User(AbstractUser):
    username = None
    first_name = None
    last_name = None
    line_user_id = models.CharField(max_length=255, unique=True, null=False, blank=False)
    profile_picture = models.URLField(max_length=200, blank=True, null=True)
    display_name = models.CharField(max_length=255, blank=True, null=True)
    status_message = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    access_token = models.CharField(max_length=1000, blank=True, null=True)  
    id_token = models.CharField(max_length=1000, blank=True, null=True)      
    gpt_photo_desc = models.TextField(blank=True, null=True) 
    user_level = models.IntegerField(blank=True, null=True, default=1)
    gpt_desc_expire_time = models.DateTimeField(blank=True, null=True) 
    last_joined = models.DateTimeField(blank=True, null=True)
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
    

###########################USEER DATABASE###########################
    
def user_documents_upload_uri(instance, filename):
    # user_id = instance.user.line_user_id
    return os.path.join(instance.user_id, instance.file_type, f'{instance.doc_id}.{instance.doc_type}')
    
def user_image_upload_uri(instance, filename):
    # user_id = instance.user.line_user_id
    return os.path.join(instance.user_id, instance.file_type, 'thumbnails', f'{instance.doc_id}_thumbnail.png')

class UserDocument(models.Model):
    doc_id = models.CharField(max_length=100, editable=False, unique=True, primary_key=True)
    # user = models.ForeignKey(User, on_delete=models.CASCADE)
    user_id = models.CharField(max_length=255, null=False, blank=False)
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
    file = models.FileField(upload_to=user_documents_upload_uri, storage=UserDocumentStorage(), null=True)
    thumbnail = models.ImageField(upload_to=user_image_upload_uri, storage=UserDocumentStorage(), blank=True, null=True)

    def __str__(self):
        return self.doc_title
    
class UserChatLog(models.Model):
    user_id = models.CharField(max_length=255)
    doc_id = models.CharField(max_length=255, null=True, blank=True)
    create_time = models.DateTimeField(default=timezone.now)
    last_update_time = models.DateTimeField(null=True, blank=True)
    dialog_session_id = models.CharField(max_length=255, unique=True)
    dialog_text = models.TextField(null=True, blank=True)
    dialog_meta = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"ChatLog for {self.user_id} (Session: {self.dialog_session_id})"
    
class AgentPersona(models.Model):
    persona_id = models.AutoField(primary_key=True)
    persona_name = models.CharField(max_length=255, unique=True)
    persona_data = models.TextField()

    def __str__(self):
        return self.persona_name
    
class UserActivityList(models.Model):
    activity_id = models.AutoField(primary_key=True)
    user_id = models.CharField(max_length=255)
    check_flag = models.IntegerField(default=0)
    priority_flag = models.IntegerField(default=10)
    activity_desc = models.TextField()
    create_date = models.DateTimeField(default=timezone.now)
    finish_date = models.DateTimeField(null=True, blank=True)
    session_id = models.CharField(max_length=255)

    def __str__(self):
        return f"Activity {self.activity_id} for User {self.user_id}"