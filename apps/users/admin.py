from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.models import Group
from django.utils.html import format_html
from .models import CustomUser, Customer, Staff, Owner
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

# ==================== PERMISSION HELPERS ====================

def is_owner_user(request):
    """Check if user is owner/superuser"""
    if hasattr(request.user, 'user_type'):
        return request.user.user_type == 'owner'
    return request.user.is_superuser

def is_staff_user(request):
    """Check if user is staff (not owner)"""
    if hasattr(request.user, 'user_type'):
        return request.user.user_type == 'staff'
    return False

# ==================== CUSTOM USER ADMIN ====================
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'mobile_no', 'user_type', 'first_name', 'last_name', 'is_active', 'date_joined']
    list_filter = ['user_type', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'mobile_no', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    # Fields that staff cannot edit
    staff_readonly_fields = ['user_type', 'is_superuser', 'user_permissions', 'groups', 'last_login', 'date_joined']
    
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email', 'mobile_no', 'primary_address', 'delivery_address')
        }),
        ('Role & Permissions', {
            'fields': ('user_type', 'is_active', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'mobile_no', 'user_type', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ['last_login', 'date_joined']
    
    # ========== PERMISSION METHODS ==========
    
    def has_module_permission(self, request):
        """Allow both staff and owners to see this module"""
        return request.user.is_staff
    
    def has_view_permission(self, request, obj=None):
        """Both staff and owners can view"""
        return request.user.is_staff
    
    def has_add_permission(self, request):
        """Only owners can add users"""
        return is_owner_user(request)
    
    def has_change_permission(self, request, obj=None):
        """Staff can only edit their own profile"""
        if not request.user.is_staff:
            return False
        
        if is_staff_user(request):
            if obj:
                # Staff can only edit their own profile
                return obj.id == request.user.id
            return True  # Can see list view
        
        return True  # Owners can edit anyone
    
    def has_delete_permission(self, request, obj=None):
        """Only owners can delete users"""
        if is_staff_user(request):
            return False
        
        # Extra protection: prevent deleting the last superuser
        if obj and obj.is_superuser:
            superuser_count = CustomUser.objects.filter(is_superuser=True).count()
            if superuser_count <= 1:
                return False
        
        return is_owner_user(request)
    
    # ========== QUERYSET AND FIELD RESTRICTIONS ==========
    
    def get_queryset(self, request):
        """
        Staff can only see:
        1. Their own profile
        2. Customer accounts
        Staff cannot see other staff or owners
        """
        qs = super().get_queryset(request)
        
        if is_staff_user(request):
            # Staff can see customers and themselves
            return qs.filter(user_type='customer') | qs.filter(id=request.user.id)
        
        return qs
    
    def get_readonly_fields(self, request, obj=None):
        """
        Make fields read-only for staff.
        """
        readonly_fields = super().get_readonly_fields(request, obj)
        
        if is_staff_user(request):
            # If staff accesses any user, make all fields read-only except their own profile
            if obj and obj.id != request.user.id:
                return [field.name for field in self.model._meta.fields]
            
            # For their own profile, add staff readonly fields
            return list(readonly_fields) + list(self.staff_readonly_fields)
        
        return readonly_fields
    
    def get_list_display(self, request):
        """
        Remove is_superuser from list display for staff.
        """
        list_display = super().get_list_display(request)
        if is_staff_user(request):
            return [field for field in list_display if field != 'is_superuser']
        return list_display
    
    def get_list_filter(self, request):
        """
        Remove is_superuser filter for staff.
        """
        list_filter = super().get_list_filter(request)
        if is_staff_user(request):
            return [field for field in list_filter if field != 'is_superuser']
        return list_filter
    
    # ========== ADMIN VIEW CUSTOMIZATIONS ==========
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        Customize the change view based on user type.
        """
        extra_context = extra_context or {}
        
        if is_staff_user(request):
            # For staff: check if they're trying to edit their own profile
            try:
                obj = self.get_queryset(request).get(pk=object_id)
                if obj.id != request.user.id:
                    from django.contrib import messages
                    messages.error(request, "You can only edit your own profile.")
                    from django.shortcuts import redirect
                    return redirect('admin:users_customuser_changelist')
            except self.model.DoesNotExist:
                from django.contrib import messages
                messages.error(request, "You don't have permission to view this user.")
                from django.shortcuts import redirect
                return redirect('admin:users_customuser_changelist')
        
        return super().change_view(request, object_id, form_url, extra_context)
    
    def save_model(self, request, obj, form, change):
        """
        Ensure user_type and is_superuser are synchronized.
        """
        # If setting user_type to owner, ensure is_superuser is True
        if obj.user_type == 'owner':
            obj.is_superuser = True
            obj.is_staff = True
        
        # If setting user_type to staff, ensure is_superuser is False
        if obj.user_type == 'staff':
            obj.is_superuser = False
            obj.is_staff = True
        
        # If setting user_type to customer, ensure is_superuser and is_staff are False
        if obj.user_type == 'customer':
            obj.is_superuser = False
            obj.is_staff = False
        
        super().save_model(request, obj, form, change)

# ==================== CUSTOMER ADMIN ====================
@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    list_display = ['username', 'email', 'mobile_no', 'first_name', 'last_name', 'delivery_address', 'is_active', 'date_joined']
    list_filter = ['is_active', 'date_joined']
    search_fields = ['username', 'email', 'mobile_no', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email', 'mobile_no', 'delivery_address')
        }),
        ('Permissions', {
            'fields': ('is_active', 'groups', 'user_permissions')
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    readonly_fields = ['last_login', 'date_joined']
    
    # ========== PERMISSION METHODS ==========
    
    def has_module_permission(self, request):
        """Allow both staff and owners to see this module"""
        return request.user.is_staff
    
    def has_view_permission(self, request, obj=None):
        """Both staff and owners can view customers"""
        return request.user.is_staff
    
    def has_add_permission(self, request):
        """Only owners can add customers"""
        return is_owner_user(request)
    
    def has_change_permission(self, request, obj=None):
        """Staff cannot edit customers"""
        if is_staff_user(request):
            return False
        return request.user.is_staff
    
    def has_delete_permission(self, request, obj=None):
        """Only owners can delete customers"""
        return is_owner_user(request)
    
    # ========== QUERYSET RESTRICTIONS ==========
    
    def get_queryset(self, request):
        """
        Staff can only see customers.
        """
        qs = super().get_queryset(request)
        
        if is_staff_user(request):
            return qs.filter(user_type='customer')
        
        return qs
    
    # ========== ADMIN VIEW CUSTOMIZATIONS ==========
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        Staff cannot access customer edit pages.
        """
        if is_staff_user(request):
            from django.contrib import messages
            messages.error(request, "You don't have permission to edit customers.")
            from django.shortcuts import redirect
            return redirect('admin:users_customer_changelist')
        return super().change_view(request, object_id, form_url, extra_context)

# ==================== STAFF ADMIN ====================
@admin.register(Staff)
class StaffAdmin(ModelAdmin):
    list_display = ['username', 'email', 'mobile_no', 'first_name', 'last_name', 'primary_address', 'is_active', 'date_joined']
    list_filter = ['is_active', 'date_joined']
    search_fields = ['username', 'email', 'mobile_no', 'first_name', 'last_name', 'primary_address']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email', 'mobile_no', 'primary_address')
        }),
        ('Permissions', {
            'fields': ('is_active', 'groups', 'user_permissions')
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    readonly_fields = ['last_login', 'date_joined']
    
    # ========== PERMISSION METHODS ==========
    
    def has_module_permission(self, request):
        """Allow both staff and owners to see this module"""
        return request.user.is_staff
    
    def has_view_permission(self, request, obj=None):
        """Both staff and owners can view"""
        return request.user.is_staff
    
    def has_add_permission(self, request):
        """Only owners can add staff"""
        return is_owner_user(request)
    
    def has_change_permission(self, request, obj=None):
        """Staff can only edit their own profile"""
        if not request.user.is_staff:
            return False
        
        if is_staff_user(request):
            if obj:
                return obj.id == request.user.id
            return True  # Can see list view (which will only show themselves)
        
        return True  # Owners can edit anyone
    
    def has_delete_permission(self, request, obj=None):
        """Only owners can delete staff"""
        if is_staff_user(request):
            return False
        return is_owner_user(request)
    
    # ========== QUERYSET RESTRICTIONS ==========
    
    def get_queryset(self, request):
        """
        Staff can only see themselves.
        Owners can see all staff.
        """
        qs = super().get_queryset(request)
        
        if is_staff_user(request):
            return qs.filter(id=request.user.id)
        
        return qs
    
    def get_readonly_fields(self, request, obj=None):
        """
        Make fields read-only for staff editing their own profile.
        """
        readonly_fields = super().get_readonly_fields(request, obj)
        
        if is_staff_user(request) and obj and obj.id == request.user.id:
            # Staff can edit basic info but not permissions
            return list(readonly_fields) + ['groups', 'user_permissions']
        
        return readonly_fields
    
    # ========== ADMIN VIEW CUSTOMIZATIONS ==========
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        Staff can only edit their own profile.
        """
        if is_staff_user(request) and str(request.user.id) != object_id:
            from django.contrib import messages
            messages.error(request, "You can only edit your own profile.")
            from django.shortcuts import redirect
            return redirect('admin:users_staff_changelist')
        
        return super().change_view(request, object_id, form_url, extra_context)

# ==================== OWNER ADMIN (SUPERUSER) ====================
@admin.register(Owner)
class OwnerAdmin(ModelAdmin):
    list_display = ['username', 'email', 'mobile_no', 'first_name', 'last_name', 'is_active', 'is_superuser', 'date_joined']
    list_filter = ['is_active', 'is_superuser', 'date_joined']
    search_fields = ['username', 'email', 'mobile_no', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email', 'mobile_no')
        }),
        ('Superuser Permissions', {
            'fields': ('is_active', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    readonly_fields = ['last_login', 'date_joined']
    
    # ========== PERMISSION METHODS ==========
    
    def has_module_permission(self, request):
        """Only owners can see this module"""
        return is_owner_user(request)
    
    def has_view_permission(self, request, obj=None):
        """Only owners can view owners"""
        return is_owner_user(request)
    
    def has_add_permission(self, request):
        """Only owners can add owners"""
        return is_owner_user(request)
    
    def has_change_permission(self, request, obj=None):
        """Only owners can change owners"""
        return is_owner_user(request)
    
    def has_delete_permission(self, request, obj=None):
        """Only owners can delete owners, with restrictions"""
        if not is_owner_user(request):
            return False
        
        # Prevent deleting the last superuser
        if obj and obj.is_superuser:
            superuser_count = Owner.objects.filter(is_superuser=True).count()
            if superuser_count <= 1:
                return False
        
        return True
    
    # ========== QUERYSET RESTRICTIONS ==========
    
    def get_queryset(self, request):
        """
        Staff cannot see any owner/superuser accounts.
        """
        qs = super().get_queryset(request)
        
        if is_staff_user(request):
            return qs.none()
        
        return qs
    
    def save_model(self, request, obj, form, change):
        """
        Ensure owners are always superusers.
        """
        obj.user_type = 'owner'
        obj.is_superuser = True
        obj.is_staff = True
        super().save_model(request, obj, form, change)

# ==================== GROUP ADMIN CUSTOMIZATION ====================
# Unregister the default Group admin and register a custom one
admin.site.unregister(Group)

@admin.register(Group)
class CustomGroupAdmin(GroupAdmin, ModelAdmin):
    """
    Custom Group admin with permission restrictions.
    """
    
    def has_module_permission(self, request):
        """Only owners can see Groups module"""
        return is_owner_user(request)
    
    def has_view_permission(self, request, obj=None):
        """Only owners can view groups"""
        return is_owner_user(request)
    
    def has_add_permission(self, request):
        """Only owners can add groups"""
        return is_owner_user(request)
    
    def has_change_permission(self, request, obj=None):
        """Only owners can change groups"""
        return is_owner_user(request)
    
    def has_delete_permission(self, request, obj=None):
        """Only owners can delete groups"""
        return is_owner_user(request)

# ==================== CUSTOM ADMIN CONTEXT ====================
# Add user_type to admin context
original_each_context = admin.site.each_context

def custom_each_context(request):
    context = original_each_context(request)
    if request.user.is_authenticated:
        # Use getattr for safety
        context['user_type'] = getattr(request.user, 'user_type', 'customer')
        context['is_staff_user'] = getattr(request.user, 'user_type', '') == 'staff'
        context['is_owner_user'] = getattr(request.user, 'user_type', '') == 'owner'
        context['is_superuser_user'] = getattr(request.user, 'is_superuser', False)
    return context

admin.site.each_context = custom_each_context