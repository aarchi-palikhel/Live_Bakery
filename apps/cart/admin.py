from django.contrib import admin
from django.utils.html import format_html
from .models import Cart, CartItem

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['added_at', 'total_price_display', 'stock_status_display']
    fields = ['product', 'quantity', 'total_price_display', 'stock_status_display', 'added_at']
    
    def total_price_display(self, obj):
        return f"Rs. {obj.total_price:.2f}"
    total_price_display.short_description = 'Total Price'
    
    def stock_status_display(self, obj):
        """Check if cart item quantity is within available stock"""
        if obj.quantity <= obj.product.stock:
            return format_html('<span style="color: green;">✓ In Stock</span>')
        else:
            return format_html('<span style="color: red;">✗ Exceeds Stock ({})</span>', obj.product.stock)
    stock_status_display.short_description = 'Stock Status'

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'item_count', 'total_price_display', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at', 'total_price_display', 'item_count']
    inlines = [CartItemInline]
    list_per_page = 20
    
    fieldsets = (
        ('Cart Information', {
            'fields': ('user', 'created_at', 'updated_at')
        }),
        ('Cart Summary', {
            'fields': ('item_count', 'total_price_display'),
            'classes': ('collapse',)
        }),
    )
    
    def item_count(self, obj):
        return obj.total_items
    item_count.short_description = 'Total Items'
    
    def total_price_display(self, obj):
        return f"Rs. {obj.total_price:.2f}"
    total_price_display.short_description = 'Total Value'
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('items', 'items__product')

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['product', 'cart_user', 'quantity', 'unit_price_display', 
                    'total_price_display', 'stock_status', 'added_at']
    list_filter = ['added_at', 'product__category']
    search_fields = ['product__name', 'cart__user__username', 'cart__user__email']
    readonly_fields = ['added_at', 'total_price_display', 'unit_price_display', 'stock_status']
    list_per_page = 30
    
    fieldsets = (
        ('Item Information', {
            'fields': ('cart', 'product', 'quantity', 'added_at')
        }),
        ('Pricing & Stock', {
            'fields': ('unit_price_display', 'total_price_display', 'stock_status'),
            'classes': ('collapse',)
        }),
    )
    
    def cart_user(self, obj):
        return obj.cart.user.username
    cart_user.short_description = 'User'
    cart_user.admin_order_field = 'cart__user__username'
    
    def unit_price_display(self, obj):
        return f"Rs. {obj.product.base_price:.2f}"
    unit_price_display.short_description = 'Unit Price'
    
    def total_price_display(self, obj):
        return f"Rs. {obj.total_price:.2f}"
    total_price_display.short_description = 'Total Price'
    
    def stock_status(self, obj):
        if obj.quantity <= obj.product.stock:
            return format_html(
                '<span style="color: green;">✓ In Stock ({})</span>', 
                obj.product.stock
            )
        else:
            return format_html(
                '<span style="color: red;">✗ Only {} available</span>', 
                obj.product.stock
            )
    stock_status.short_description = 'Stock Check'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'cart', 'cart__user')