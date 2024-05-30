from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.validators import FileExtensionValidator
import uuid
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
    user_level = models.IntegerField(blank=True, null=True)

    date_joined = models.DateTimeField(default=timezone.now)
    
    groups = models.ManyToManyField(Group, related_name='custom_user_set')
    user_permissions = models.ManyToManyField(Permission, related_name='custom_user_set_permissions')

    def __str__(self):
        return self.line_user_id
    
class Document(models.Model):
    doc_id = models.CharField(max_length=255, unique=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    doc_type = models.CharField(max_length=10)
    doc_loc = models.CharField(max_length=255)
    doc_uri = models.CharField(max_length=255)
    doc_title = models.CharField(max_length=255)
    doc_desc = models.TextField()
    doc_md5 = models.CharField(max_length=255)
    doc_text = models.TextField(blank=True, null=True)
    doc_meta = models.TextField(blank=True, null=True)
    share_flag = models.BooleanField(default=False)
    audit_flag = models.BooleanField(default=False)
    display_date = models.DateTimeField(null=True, blank=True)
    expire_date = models.DateTimeField(null=True, blank=True)
    doc_createdate = models.DateTimeField(auto_now_add=True)
    doc_revisedate = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.doc_title

###FOR FORUM FILES###

def generate_forum_uuid():
    return str(uuid.uuid4())

def document_directory_path(instance, filename):
    return 'forum/documents/{0}/{1}'.format(instance.forum.folderId, filename)

def snapshot_directory_path(instance, filename):
    return 'forum/documents/{0}/snapshots/{1}'.format(instance.forum.folderId, filename)

class ForumDocument(models.Model):
    forum = models.ForeignKey('Forum', related_name='forum_documents', on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True, help_text="Leave blank to use filename as title.") 
    document = models.FileField(
        upload_to=document_directory_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf',])],
        help_text="Only PDF Allowed."
    )
    snapshot = models.ImageField(upload_to=snapshot_directory_path, blank=True, null=True)
    upload_time = models.DateTimeField(auto_now=True)
    click_count = models.IntegerField(default=0)

    def __str__(self):
        return self.document.name

    def save(self, *args, **kwargs):
        # If the title is blank, set it to the filename without the extension
        if not self.title:
            filename = self.document.name
            self.title = filename.rsplit('.', 1)[0]

        super().save(*args, **kwargs)  # Save the document first to ensure it has a file path

        # Check if a snapshot does not already exist and the document is a PDF
        if not self.snapshot and self.document.name.endswith('.pdf'):
            self.generate_pdf_snapshot()
            super().save(*args, **kwargs)  # Save again to save the snapshot field

    def generate_pdf_snapshot(self):
        import fitz 
        from django.core.files.base import ContentFile
        doc = fitz.open(self.document.path)
        page = doc.load_page(0)
        pix = page.get_pixmap()
        img_bytes = pix.tobytes("png")  
        img_content_file = ContentFile(img_bytes, name='temp.png')  
        self.snapshot.save(f"{self.title}_snapshot.png", img_content_file, save=True)
        doc.close()

def forum_directory_path(instance, filename):
    return 'forum/logos/{0}/{1}'.format(instance.folderId, filename)

from cms.models.pluginmodel import CMSPlugin

class Forum(CMSPlugin):
    folderId = models.CharField(max_length=36, default=generate_forum_uuid, primary_key=True, editable=False)
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(
        upload_to=forum_directory_path, 
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['png', 'jpg', 'jpeg'])]
    )
    upload_time = models.DateTimeField(auto_now=True)
    click_count = models.IntegerField(default=0)

    def get_logo_url(self):
        if self.logo and hasattr(self.logo, 'url'):
            return self.logo.url
        else:
            return settings.MEDIA_URL + 'MainLogo/ResidemyLogo.jpg'

    def __str__(self):
        return self.title

class ForumPluginModel(CMSPlugin):
    forum = models.ForeignKey(Forum, on_delete=models.CASCADE)

    def __str__(self):
        return self.forum.title

# from django.contrib.auth.models import User

# class UserFile(models.Model):
#     user = models.ForeignKey(User, related_name='files', on_delete=models.CASCADE)
#     uploaded_file = models.FileField(upload_to='user_files/%Y/%m/%d/')
#     uploaded_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"File {self.uploaded_file.name} uploaded by {self.user.username}"