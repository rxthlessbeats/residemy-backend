from django.contrib import admin
from .models import Forum, ForumDocument

class ForumDocumentInline(admin.TabularInline):
    model = ForumDocument
    extra = 1  # Number of extra forms to display
    exclude = ('snapshot', 'upload_time', 'click_count',)
    fields = ('title', 'document', 'click_count')
    readonly_fields = ('click_count',)

@admin.register(Forum)
class ForumAdmin(admin.ModelAdmin):
    list_display = ('title', 'folderId', 'upload_time', )
    inlines = [ForumDocumentInline]
    readonly_fields = ('click_count',)