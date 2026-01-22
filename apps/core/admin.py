from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.shortcuts import get_object_or_404
from .models import ContactMessage, ContactMessageReply
from unfold.admin import ModelAdmin, TabularInline
from django.contrib import admin

# Configure admin site
admin.site.site_header = "Live Bakery Administration"
admin.site.site_title = "Live Bakery Admin"
admin.site.index_title = "Dashboard"
admin.site.index_template = 'admin/index.html' 


class ContactMessageReplyInline(TabularInline):
    model = ContactMessageReply
    extra = 0
    readonly_fields = ['reply_message', 'admin_user', 'email_sent', 'email_sent_at', 'created_at']
    fields = ['reply_message', 'admin_user', 'email_sent', 'email_sent_at', 'created_at']
    
    def has_add_permission(self, request, obj=None):
        """Prevent adding replies through inline - use quick reply instead"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing replies through inline"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deleting replies through inline"""
        return False
    
    def get_readonly_fields(self, request, obj=None):
        """Make all fields read-only"""
        return ['reply_message', 'admin_user', 'email_sent', 'email_sent_at', 'created_at']
    
    def save_model(self, request, obj, form, change):
        if not change:  # New reply
            obj.admin_user = request.user
        super().save_model(request, obj, form, change)


@admin.register(ContactMessage)
class ContactMessageAdmin(ModelAdmin):
    list_display = ['full_name', 'email', 'subject', 'status', 'reply_count', 'created_at', 'reply_actions']
    list_filter = ['status', 'subject', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'message']
    readonly_fields = ['created_at', 'updated_at', 'replied_at', 'ip_address', 'user_agent']
    inlines = [ContactMessageReplyInline]
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('Message Details', {
            'fields': ('subject', 'message', 'status')
        }),
        ('System Information', {
            'fields': ('ip_address', 'user_agent', 'created_at', 'updated_at', 'replied_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent adding contact messages through admin - they should come from the contact form"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing contact messages - they should remain as submitted by customers"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deleting contact messages - they should be preserved for records"""
        return False
    
    def has_view_permission(self, request, obj=None):
        """Allow both staff and owners to view contact messages"""
        return request.user.is_staff
    
    def get_readonly_fields(self, request, obj=None):
        """Make all fields read-only"""
        if obj:  # Editing an existing object
            return [field.name for field in self.model._meta.fields]
        return self.readonly_fields
    
    def reply_count(self, obj):
        count = obj.replies.count()
        if count > 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">{} replies</span>',
                count
            )
        return format_html('<span style="color: #999;">No replies</span>')
    reply_count.short_description = 'Replies'
    
    def reply_actions(self, obj):
        if obj.pk:
            return format_html(
                '<span style="color: #666;">View Only</span>'
            )
        return '-'
    reply_actions.short_description = 'Actions'
    reply_actions.allow_tags = True


@admin.register(ContactMessageReply)
class ContactMessageReplyAdmin(ModelAdmin):
    list_display = ['contact_message', 'admin_user', 'email_sent', 'created_at', 'email_actions']
    list_filter = ['email_sent', 'created_at', 'admin_user']
    search_fields = ['contact_message__first_name', 'contact_message__last_name', 'reply_message']
    readonly_fields = ['email_sent_at', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Reply Details', {
            'fields': ('contact_message', 'admin_user', 'reply_message')
        }),
        ('Email Status', {
            'fields': ('email_sent', 'email_sent_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent adding replies through admin - they should be created via quick reply"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing replies - they should remain as originally sent"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deleting replies - they should be preserved for records"""
        return False
    
    def has_view_permission(self, request, obj=None):
        """Allow both staff and owners to view replies"""
        return request.user.is_staff
    
    def get_readonly_fields(self, request, obj=None):
        """Make all fields read-only"""
        if obj:  # Viewing an existing object
            return [field.name for field in self.model._meta.fields]
        return self.readonly_fields
    
    def email_actions(self, obj):
        if obj.email_sent:
            return format_html(
                '<span style="color: green;">✓ Sent on {}</span>',
                obj.email_sent_at.strftime('%Y-%m-%d %H:%M') if obj.email_sent_at else 'Unknown'
            )
        else:
            return format_html('<span style="color: #999;">Not sent</span>')
    email_actions.short_description = 'Email Status'
    email_actions.allow_tags = True
    
    def save_model(self, request, obj, form, change):
        if not change:  # New reply
            obj.admin_user = request.user
        super().save_model(request, obj, form, change)