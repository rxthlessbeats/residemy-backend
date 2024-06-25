from django.contrib import admin
from .models import User, Document

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('line_user_id', 'password')}),
        ('Personal info', {'fields': ('display_name', 'email', 'profile_picture', 'status_message', 'gpt_photo_desc', 'gpt_desc_expire_time','user_level')}),
        # ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_joined', 'date_joined')}),
    )
    list_display = ('line_user_id', 'display_name', 'email', 'user_level')
    search_fields = ('line_user_id', 'display_name', 'email')
    ordering = ('line_user_id',)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('doc_id', 'doc_title', 'doc_type', 'user', 'display_date', 'expire_date', 'doc_createdate', 'doc_revisedate')
    search_fields = ('doc_title', 'user__username', 'doc_id')
    list_filter = ('doc_type', 'share_flag', 'audit_flag', 'display_date', 'expire_date')
    ordering = ('-doc_createdate',)