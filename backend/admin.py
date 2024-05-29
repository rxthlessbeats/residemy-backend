from django.contrib import admin
from .models import Forum, ForumDocument, User

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('line_user_id', 'password')}),
        ('Personal info', {'fields': ('display_name', 'email', 'profile_picture', 'status_message')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('line_user_id', 'display_name', 'email', 'is_staff')
    search_fields = ('line_user_id', 'display_name', 'email')
    ordering = ('line_user_id',)

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