from cms.models.pluginmodel import CMSPlugin
from django.conf import settings
from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.files.base import ContentFile
import fitz
import uuid

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
        doc = fitz.open(self.document.path)
        page = doc.load_page(0)  # first page
        pix = page.get_pixmap()
        img_bytes = pix.tobytes("png")  # Get PNG bytes
        img_content_file = ContentFile(img_bytes, name='temp.png')  # Create a ContentFile
        self.snapshot.save(f"{self.title}_snapshot.png", img_content_file, save=True)
        doc.close()

def forum_directory_path(instance, filename):
    return 'forum/logos/{0}/{1}'.format(instance.folderId, filename)

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
    

