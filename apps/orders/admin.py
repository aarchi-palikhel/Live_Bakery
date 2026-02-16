from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.http import HttpResponse
from decimal import Decimal
from .models import Order, OrderItem, CakeDesignReference
from unfold.admin import ModelAdmin
from import_export.admin import ImportExportModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm, SelectableFieldsExportForm
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render


class CakeDesignReferenceInline(admin.TabularInline):
    """Inline for cake design references in OrderItem"""
    model = CakeDesignReference
    extra = 0
    max_num = 5
    readonly_fields = ['uploaded_at', 'design_image_preview', 'order_info']
    fields = ['title', 'image', 'design_image_preview', 'description', 'uploaded_at', 'order_info']
    
    def design_image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px;" />',
                obj.image.url
            )
        return "No image"
    design_image_preview.short_description = 'Preview'
    
    def order_info(self, obj):
        if obj.order:
            url = reverse('admin:orders_order_change', args=[obj.order.id])
            return format_html('<a href="{}">Order #{}</a>', url, obj.order.id)
        return "No order"
    order_info.short_description = 'Order'


class OrderItemInline(admin.TabularInline):
    """Inline for order items in Order"""
    model = OrderItem
    extra = 0
    readonly_fields = ['total_price_display', 'is_cake_display', 'cake_details']
    fields = ['product', 'quantity', 'price', 'total_price_display', 
              'is_cake_display', 'cake_details']
    
    def total_price_display(self, obj):
        return f"Rs. {obj.total_price:.2f}"
    total_price_display.short_description = 'Total'
    
    def is_cake_display(self, obj):
        if obj.is_cake:
            return format_html('<span style="color: green;">✓ Cake</span>')
        return format_html('<span style="color: gray;">Regular</span>')
    is_cake_display.short_description = 'Type'
    
    def cake_details(self, obj):
        if obj.is_cake:
            details = []
            if obj.cake_flavor:
                details.append(f"Flavor: {obj.display_flavor}")
            if obj.cake_weight:
                details.append(f"Weight: {obj.display_weight}")
            if obj.cake_tiers:
                details.append(f"Tiers: {obj.cake_tiers}")
            if obj.message_on_cake:
                details.append(f"Message: {obj.message_on_cake}")
            if obj.delivery_date:
                details.append(f"Delivery: {obj.delivery_date}")
            return format_html('<br>'.join(details))
        return "—"
    cake_details.short_description = 'Cake Customization'
    
    def has_add_permission(self, request, obj=None):
        # Prevent adding items directly
        return False


@admin.register(Order)
class OrderAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = ['order_id_display', 'order_number', 'user_info', 'total_amount_display', 
                    'status_display', 'payment_method_display', 'payment_status_display',
                    'delivery_type_display', 'item_count', 'created_at', 'download_receipt_button']
    list_filter = ['status', 'payment_method', 'payment_status', 'delivery_type', 'created_at']
    search_fields = ['order_number', 'user__username', 'user__email', 
                     'user__first_name', 'user__last_name', 'phone_number']
    readonly_fields = ['order_number', 'created_at', 'updated_at', 'total_amount_display',
                      'item_count_display', 'order_link', 'user_info_display',
                      'subtotal_display', 'delivery_fee_display', 'payment_status_display',
                      'download_receipt_link']
    inlines = [OrderItemInline]
    list_per_page = 20
    date_hierarchy = 'created_at'
    
    import_form_class = ImportForm
    export_form_class = ExportForm
    
    # Add custom admin actions for order status updates
    actions = [
        'mark_as_paid', 
        'mark_as_confirmed', 
        'mark_as_baking', 
        'mark_as_ready', 
        'mark_as_completed', 
        'mark_as_cancelled'
    ]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_link', 'order_number', 'user_info_display', 'status', 
                      'delivery_type', 'item_count_display', 'download_receipt_link')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'payment_status', 'payment_transaction'),
            'classes': ('collapse',)
        }),
        ('Amount Breakdown', {
            'fields': ('subtotal_display', 'delivery_fee_display', 'total_amount_display'),
            'classes': ('collapse',)
        }),
        ('Delivery Information', {
            'fields': ('delivery_address', 'phone_number', 'special_instructions')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def order_id_display(self, obj):
        return format_html('<strong>#{}</strong>', obj.id)
    order_id_display.short_description = 'ID'
    order_id_display.admin_order_field = 'id'
    
    def user_info(self, obj):
        url = reverse('admin:users_customuser_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_info.short_description = 'Customer'
    user_info.admin_order_field = 'user__username'
    
    def user_info_display(self, obj):
        user = obj.user
        info = [
            f"<strong>Username:</strong> {user.username}",
            f"<strong>Email:</strong> {user.email}",
            f"<strong>Phone:</strong> {obj.phone_number or 'Not provided'}",
        ]
        if user.first_name or user.last_name:
            info.insert(1, f"<strong>Name:</strong> {user.first_name} {user.last_name}".strip())
        
        url = reverse('admin:users_customuser_change', args=[user.id])
        info.append(f'<a href="{url}" class="button">View Customer Details</a>')
        return mark_safe('<br>'.join(info))
    user_info_display.short_description = 'Customer Information'
    
    def total_amount_display(self, obj):
        return f"Rs. {obj.total_amount:.2f}"
    total_amount_display.short_description = 'Total Amount'
    
    def status_display(self, obj):
        return format_html(
            '<span class="px-2 py-1 rounded text-xs font-bold {}">{}</span>',
            obj.get_status_display_class,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def payment_method_display(self, obj):
        payment_colors = {
            'cod': 'bg-blue-100 text-blue-800',
            'esewa': 'bg-green-100 text-green-800',
            'online': 'bg-green-100 text-green-800',
            'card': 'bg-purple-100 text-purple-800',
        }
        color_class = payment_colors.get(obj.payment_method, 'bg-gray-100 text-gray-800')
        return format_html(
            '<span class="px-2 py-1 rounded text-xs font-bold {}">{}</span>',
            color_class,
            obj.get_payment_method_display()
        )
    payment_method_display.short_description = 'Payment Method'
    
    def payment_status_display(self, obj):
        return format_html(
            '<span class="px-2 py-1 rounded text-xs font-bold {}">{}</span>',
            obj.get_payment_status_display_class,
            obj.get_payment_status_display()
        )
    payment_status_display.short_description = 'Payment Status'
    
    def delivery_type_display(self, obj):
        delivery_colors = {
            'delivery': 'bg-blue-100 text-blue-800',
            'pickup': 'bg-orange-100 text-orange-800',
        }
        color_class = delivery_colors.get(obj.delivery_type, 'bg-gray-100 text-gray-800')
        # Get display value from DELIVERY_CHOICES
        delivery_choices_dict = dict(obj.DELIVERY_CHOICES)
        display_value = delivery_choices_dict.get(obj.delivery_type, obj.delivery_type)
        return format_html(
            '<span class="px-2 py-1 rounded text-xs font-bold {}">{}</span>',
            color_class,
            display_value
        )
    delivery_type_display.short_description = 'Delivery Type'
    
    def item_count_display(self, obj):
        return obj.item_count
    item_count_display.short_description = 'Total Items'
    
    def subtotal_display(self, obj):
        return f"Rs. {obj.subtotal:.2f}"
    subtotal_display.short_description = 'Subtotal (before delivery)'
    
    def delivery_fee_display(self, obj):
        return f"Rs. {obj.delivery_fee:.2f}"
    delivery_fee_display.short_description = 'Delivery Fee'
    
    def order_link(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.id])
        return format_html('<a href="{}">Edit Order #{}</a>', url, obj.id)
    order_link.short_description = 'Order'
    
    def download_receipt_button(self, obj):
        """Display download receipt button in list view"""
        url = reverse('admin:download_order_receipt', args=[obj.id])
        return format_html(
            '<a href="{}" class="button" style="padding: 5px 10px; background-color: #d97706; color: white; text-decoration: none; border-radius: 4px; font-size: 12px;">Download</a>',
            url
        )
    download_receipt_button.short_description = 'Receipt'
    
    def download_receipt_link(self, obj):
        """Display download receipt link in detail view"""
        url = reverse('admin:download_order_receipt', args=[obj.id])
        return format_html(
            '<a href="{}" class="button" style="padding: 10px 20px; background-color: #d97706; color: white; text-decoration: none; border-radius: 6px; font-size: 14px; display: inline-block;">📄 Download Receipt/Invoice</a>',
            url
        )
    download_receipt_link.short_description = 'Download Receipt'
    
    def get_urls(self):
        """Add custom URL for downloading receipt"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:order_id>/download-receipt/',
                self.admin_site.admin_view(self.download_receipt_view),
                name='download_order_receipt',
            ),
        ]
        return custom_urls + urls
    
    def download_receipt_view(self, request, order_id):
        """Generate and download receipt PDF for an order"""
        try:
            order = Order.objects.get(id=order_id)
            
            # Import the invoice generator
            from utils.invoice_generator import InvoiceGenerator
            
            # Generate the PDF
            generator = InvoiceGenerator(order)
            pdf = generator.generate()
            
            # Create HTTP response with PDF
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Live_Bakery_Receipt_{order.order_number}.pdf"'
            
            return response
            
        except Order.DoesNotExist:
            from django.contrib import messages
            messages.error(request, f'Order with ID {order_id} not found.')
            return HttpResponse('Order not found', status=404)
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f'Error generating receipt: {str(e)}')
            return HttpResponse(f'Error generating receipt: {str(e)}', status=500)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'payment_transaction').prefetch_related('items', 'items__product')
    
    def has_add_permission(self, request):
        # Orders should be created through checkout process, not manually in admin
        return False
    
    # Custom admin actions for order status updates
    
    def mark_as_paid(self, request, queryset):
        """Mark selected orders as paid - THIS ADDS TO REVENUE"""
        updated = queryset.update(payment_status='paid')
        self.message_user(request, f"✅ {updated} order(s) marked as paid. These orders are now counted as revenue.")
    mark_as_paid.short_description = "✅ Mark as paid"
    
    def mark_as_confirmed(self, request, queryset):
        """Mark selected orders as confirmed"""
        updated_count = queryset.update(status='confirmed')
        
        if updated_count > 0:
            self.message_user(request, f"✅ {updated_count} order(s) marked as confirmed. Email notifications will be sent automatically.")
        else:
            self.message_user(request, "No orders were updated (they may already be confirmed).")
    mark_as_confirmed.short_description = "📋 Mark as confirmed"
    
    def mark_as_baking(self, request, queryset):
        """Mark selected orders as baking"""
        updated_count = queryset.update(status='baking')
        
        if updated_count > 0:
            self.message_user(request, f"✅ {updated_count} order(s) marked as baking. Email notifications will be sent automatically.")
        else:
            self.message_user(request, "No orders were updated (they may already be baking).")
    mark_as_baking.short_description = "👨‍🍳 Mark as baking"
    
    def mark_as_ready(self, request, queryset):
        """Mark selected orders as ready for pickup/delivery
        
        This action marks orders as ready, which means:
        - For pickup orders: Customer can come to collect their order
        - For delivery orders: Order is ready to be dispatched for delivery
        
        Customers will receive an email notification with appropriate instructions.
        """
        updated_count = queryset.update(status='ready')
        
        if updated_count > 0:
            self.message_user(request, f"✅ {updated_count} order(s) marked as ready for pickup/delivery. Email notifications will be sent automatically.")
        else:
            self.message_user(request, "No orders were updated (they may already be ready).")
    mark_as_ready.short_description = "📦 Mark as ready (pickup/delivery)"
    
    def mark_as_completed(self, request, queryset):
        """Mark selected orders as completed"""
        updated_count = queryset.update(status='completed')
        
        if updated_count > 0:
            self.message_user(request, f"✅ {updated_count} order(s) marked as completed. Email notifications will be sent automatically.")
        else:
            self.message_user(request, "No orders were updated (they may already be completed).")
    mark_as_completed.short_description = "🏁 Mark as completed"
    
    def mark_as_cancelled(self, request, queryset):
        """Mark selected orders as cancelled"""
        updated_count = queryset.update(status='cancelled')
        
        if updated_count > 0:
            self.message_user(request, f"❌ {updated_count} order(s) marked as cancelled. Email notifications will be sent automatically.")
        else:
            self.message_user(request, "No orders were updated (they may already be cancelled).")
    mark_as_cancelled.short_description = "❌ Mark as cancelled"
    
@admin.register(OrderItem)
class OrderItemAdmin(ModelAdmin):
    list_display = ['id_display', 'order_info', 'product_info', 'quantity', 
                    'price_display', 'total_price_display', 'is_cake_display', 
                    'created_at']
    list_filter = ['product__is_cake', 'product__category', 'created_at']
    search_fields = ['order__order_number', 'product__name', 'order__user__username']
    readonly_fields = ['total_price_display', 'order_link', 'product_link', 
                      'cake_details_display', 'created_at_display']
    inlines = [CakeDesignReferenceInline]
    list_per_page = 30
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('order_link', 'product_link', 'quantity', 'price', 'total_price_display')
        }),
        ('Cake Customization', {
            'fields': ('is_cake_display', 'cake_flavor', 'cake_custom_flavor', 
                      'cake_weight', 'cake_custom_weight', 'cake_tiers', 
                      'message_on_cake', 'delivery_date', 'special_instructions'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at_display', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def id_display(self, obj):
        return format_html('<strong>#{}</strong>', obj.id)
    id_display.short_description = 'ID'
    id_display.admin_order_field = 'id'
    
    def order_info(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.order.id])
        return format_html(
            '<a href="{}">Order #{}</a><br><small>{}</small>',
            url, obj.order.id, obj.order.order_number
        )
    order_info.short_description = 'Order'
    order_info.admin_order_field = 'order__id'
    
    def product_info(self, obj):
        url = reverse('admin:products_product_change', args=[obj.product.id])
        return format_html(
            '<a href="{}">{}</a><br><small>{}</small>',
            url, obj.product.name, obj.product.category.name
        )
    product_info.short_description = 'Product'
    
    def price_display(self, obj):
        return f"Rs. {obj.price:.2f}"
    price_display.short_description = 'Unit Price'
    
    def total_price_display(self, obj):
        return f"Rs. {obj.total_price:.2f}"
    total_price_display.short_description = 'Total Price'
    
    def is_cake_display(self, obj):
        if obj.is_cake:
            return format_html('<span style="color: green; font-weight: bold;">🎂 CAKE</span>')
        return format_html('<span style="color: gray;">Regular Item</span>')
    is_cake_display.short_description = 'Product Type'
    
    def cake_details_display(self, obj):
        if obj.is_cake:
            details = []
            if obj.cake_flavor:
                flavor = obj.display_flavor
                details.append(f"<strong>Flavor:</strong> {flavor}")
            if obj.cake_weight:
                weight = obj.display_weight
                details.append(f"<strong>Weight:</strong> {weight}")
            if obj.cake_tiers:
                details.append(f"<strong>Tiers:</strong> {obj.cake_tiers}")
            if obj.message_on_cake:
                details.append(f"<strong>Message:</strong> {obj.message_on_cake}")
            if obj.delivery_date:
                details.append(f"<strong>Delivery Date:</strong> {obj.delivery_date}")
            if obj.special_instructions:
                details.append(f"<strong>Instructions:</strong> {obj.special_instructions}")
            
            if details:
                return mark_safe('<br>'.join(details))
        return format_html('<span style="color: gray; font-style: italic;">No customization</span>')
    cake_details_display.short_description = 'Customization Details'
    
    def order_link(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.order.id])
        return format_html(
            '<a href="{}">Order #{}</a> ({})',
            url, obj.order.id, obj.order.order_number
        )
    order_link.short_description = 'Parent Order'
    
    def product_link(self, obj):
        url = reverse('admin:products_product_change', args=[obj.product.id])
        return format_html('<a href="{}">{}</a>', url, obj.product.name)
    product_link.short_description = 'Product'
    
    def created_at_display(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
    created_at_display.short_description = 'Created At'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'order', 'product', 'product__category', 'order__user'
        )
    
    def has_add_permission(self, request):
        # Order items should be created through order process
        return False


@admin.register(CakeDesignReference)
class CakeDesignReferenceAdmin(ModelAdmin):
    list_display = ['id_display', 'order_info', 'product_info', 'title', 
                    'image_preview', 'uploaded_at']
    list_filter = ['uploaded_at', 'order__status']
    search_fields = ['title', 'description', 'order__order_number', 
                     'order_item__product__name', 'order__user__username']
    readonly_fields = ['order_link', 'order_item_link', 'product_info_display',
                      'image_preview_large', 'uploaded_at_display']
    list_per_page = 20
    date_hierarchy = 'uploaded_at'
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_link', 'order_item_link', 'product_info_display')
        }),
        ('Design Details', {
            'fields': ('title', 'description')
        }),
        ('Image', {
            'fields': ('image', 'image_preview_large')
        }),
        ('Timestamps', {
            'fields': ('uploaded_at_display', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def id_display(self, obj):
        return format_html('<strong>#{}</strong>', obj.id)
    id_display.short_description = 'ID'
    id_display.admin_order_field = 'id'
    
    def order_info(self, obj):
        if obj.order:
            url = reverse('admin:orders_order_change', args=[obj.order.id])
            return format_html(
                '<a href="{}">Order #{}</a><br><small>{}</small>',
                url, obj.order.id, obj.order.order_number
            )
        return "—"
    order_info.short_description = 'Order'
    order_info.admin_order_field = 'order__id'
    
    def product_info(self, obj):
        if obj.order_item and obj.order_item.product:
            url = reverse('admin:products_product_change', args=[obj.order_item.product.id])
            return format_html(
                '<a href="{}">{}</a><br><small>Qty: {}</small>',
                url, obj.order_item.product.name, obj.order_item.quantity
            )
        return "—"
    product_info.short_description = 'Product'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                obj.image.url
            )
        return "No image"
    image_preview.short_description = 'Preview'
    
    def image_preview_large(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 300px; max-width: 100%;" /><br>'
                '<a href="{}" target="_blank">View Full Image</a>',
                obj.image.url, obj.image.url
            )
        return "No image"
    image_preview_large.short_description = 'Image Preview'
    
    def order_link(self, obj):
        if obj.order:
            url = reverse('admin:orders_order_change', args=[obj.order.id])
            return format_html(
                '<a href="{}">Order #{}</a> ({})',
                url, obj.order.id, obj.order.order_number
            )
    order_link.short_description = 'Parent Order'
    
    def order_item_link(self, obj):
        if obj.order_item:
            url = reverse('admin:orders_orderitem_change', args=[obj.order_item.id])
            return format_html(
                '<a href="{}">Order Item #{}</a>',
                url, obj.order_item.id
            )
    order_item_link.short_description = 'Order Item'
    
    def product_info_display(self, obj):
        if obj.order_item and obj.order_item.product:
            product = obj.order_item.product
            details = [
                f"<strong>Product:</strong> {product.name}",
                f"<strong>Category:</strong> {product.category.name}",
                f"<strong>Quantity:</strong> {obj.order_item.quantity}",
            ]
            
            if obj.order_item.is_cake:
                details.append(f"<strong>Type:</strong> 🎂 Cake")
                if obj.order_item.cake_flavor:
                    details.append(f"<strong>Flavor:</strong> {obj.order_item.display_flavor}")
                if obj.order_item.cake_weight:
                    details.append(f"<strong>Weight:</strong> {obj.order_item.display_weight}")
            
            return mark_safe('<br>'.join(details))
    product_info_display.short_description = 'Product Details'
    
    def uploaded_at_display(self, obj):
        return obj.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')
    uploaded_at_display.short_description = 'Uploaded At'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'order', 'order_item', 'order_item__product', 'order_item__product__category'
        ).prefetch_related('order__user')
    
    def has_add_permission(self, request):
        # Design references should be created through order process
        return False