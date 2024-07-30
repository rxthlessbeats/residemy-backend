from django.core.files.storage import FileSystemStorage
import os
from django.conf import settings

class UserDocumentStorage(FileSystemStorage):
    def __init__(self, location=None, base_url=None):
        if location is None:
            location = os.path.join(settings.BASE_DIR, 'userdbs')
        if base_url is None:
            base_url = '/userdbs/'
        super().__init__(location, base_url)

    def get_available_name(self, name, max_length=None):
        return name

    def path(self, name):
        path = os.path.join(self.location, name)
        return os.path.normpath(path)
