from django.contrib import admin
from .models import ContactMessage

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'subject', 'status', 'created_at']
    list_filter = ['status', 'subject', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'message']
    readonly_fields = ['created_at', 'updated_at', 'ip_address']
    
    def mark_as_read(self, request, queryset):
        queryset.update(status='read')
    mark_as_read.short_description = "Mark as read"
    
    def mark_as_replied(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='replied', replied_at=timezone.now())
    mark_as_replied.short_description = "Mark as replied"
    
    actions = ['mark_as_read', 'mark_as_replied']