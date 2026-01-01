from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser, Customer, Address

class AddressInline(admin.TabularInline):
    model = Address
    extra = 1
    fields = ('address_type', 'street_address', 'city', 'municipality', 'ward_number', 'tole', 'landmark', 'is_default', 'get_full_address')
    readonly_fields = ('get_full_address',)
    
    def get_full_address(self, obj):
        return obj.get_full_address()
    get_full_address.short_description = "Full Address"

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'mobile_no', 'user_type', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined']
    list_filter = ['user_type', 'is_staff', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'mobile_no', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email', 'mobile_no', 'address', 'user_type')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'mobile_no', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ['last_login', 'date_joined']

@admin.register(Customer)
class CustomerAdmin(UserAdmin):
    list_display = ['username', 'email', 'mobile_no', 'first_name', 'last_name', 'is_active', 'date_joined']
    list_filter = ['is_active', 'date_joined']
    search_fields = ['username', 'email', 'mobile_no', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email', 'mobile_no', 'address')
        }),
        ('Permissions', {
            'fields': ('is_active', 'groups', 'user_permissions')
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'mobile_no', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ['last_login', 'date_joined']
    inlines = [AddressInline]
    
    def get_queryset(self, request):
        return self.model.objects.all()
    
    def save_model(self, request, obj, form, change):
        # Ensure customer is never staff or superuser
        obj.is_staff = False
        obj.is_superuser = False
        obj.user_type = 'customer'
        super().save_model(request, obj, form, change)

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['customer', 'address_type', 'get_full_address', 'city', 'is_default', 'created_at']
    list_filter = ['address_type', 'city', 'is_default', 'created_at']
    search_fields = ['customer__username', 'customer__email', 'street_address', 'city', 'municipality']
    list_editable = ['is_default']
    readonly_fields = ['created_at', 'updated_at', 'get_full_address_display']
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('customer',)
        }),
        ('Address Details', {
            'fields': ('address_type', 'street_address', 'city', 'municipality', 'ward_number')
        }),
        ('Location Details', {
            'fields': ('tole', 'landmark')
        }),
        ('Preferences', {
            'fields': ('is_default',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'get_full_address_display'),
            'classes': ('collapse',)
        }),
    )
    
    def get_full_address_display(self, obj):
        return obj.get_full_address()
    get_full_address_display.short_description = "Full Address"