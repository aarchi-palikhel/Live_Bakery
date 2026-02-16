# admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, ProductDescription
from unfold.admin import ModelAdmin


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ['name', 'slug', 'display_image', 'product_count', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'preview_image']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Image', {
            'fields': ('image', 'preview_image')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />', obj.image.url)
        return "-"
    display_image.short_description = "Image"
    
    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="200" height="200" style="object-fit: cover; border-radius: 10px;" />', obj.image.url)
        return "No image uploaded"
    preview_image.short_description = "Image Preview"
    
    def product_count(self, obj):
        return obj.products.filter(available=True).count()
    product_count.short_description = "Products"

@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ['name', 'category', 'display_price', 'display_stock', 'display_image', 'available', 'is_featured', 'is_cake', 'in_stock', 'created_at']
    list_filter = ['category', 'available', 'is_featured', 'is_cake', 'in_stock', 'created_at']
    search_fields = ['name', 'short_description', 'description', 'category__name']
    list_editable = ['available', 'is_featured', 'is_cake', 'in_stock']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'preview_images', 'display_weight']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'category', 'short_description', 'description')
        }),
        ('Pricing & Availability', {
            'fields': ('base_price', 'available', 'in_stock', 'is_featured')
        }),
        ('Stock Management', {
            'fields': ('stock_quantity',),
            'description': 'Set to 0 for unlimited stock (cakes/made-to-order items). Set to specific number for inventory tracking.',
        }),
        ('Product Details', {
            'fields': ('weight', 'display_weight')
        }),
        ('Cake Specific Options', {
            'fields': ('is_cake', 'available_flavors', 'max_tiers', 'cake_weight', 'allow_custom_design', 'allow_reference_image'),
            'classes': ('collapse',)
        }),
        ('Product Images', {
            'fields': ('image', 'image_2', 'image_3', 'image_4', 'preview_images'),
            'description': 'Upload product images. The first image will be used as the main product image.',
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def display_price(self, obj):
        return f"Rs. {obj.base_price}"
    display_price.short_description = "Price"
    
    def display_stock(self, obj):
        """Display stock status with color coding"""
        if obj.stock_quantity == 0:
            return format_html('<span style="color: #10b981; font-weight: 500;">Made to Order</span>')
        elif obj.stock_quantity <= 5:
            return format_html('<span style="color: #f59e0b; font-weight: 500;">{} left</span>', obj.stock_quantity)
        else:
            return format_html('<span style="color: #3b82f6; font-weight: 500;">{} in stock</span>', obj.stock_quantity)
    display_stock.short_description = "Stock"
    
    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />', obj.image.url)
        return "-"
    display_image.short_description = "Image"
    
    def preview_images(self, obj):
        """Show all product images"""
        if not obj.pk:
            return "Save the product first to see image previews."
        
        html = '<div style="display: flex; gap: 10px; flex-wrap: wrap;">'
        images = obj.get_all_images()
        
        if not images:
            return "No images uploaded yet."
        
        for idx, img in enumerate(images, 1):
            html += f'''
                <div style="text-align: center;">
                    <img src="{img.url}" width="150" height="150" style="object-fit: cover; border-radius: 8px; border: 2px solid #ddd;" />
                    <p style="margin: 5px 0 0 0; font-size: 12px; color: #666;">Image {idx}</p>
                </div>
            '''
        
        html += '</div>'
        return format_html(html)
    preview_images.short_description = "Image Previews"

@admin.register(ProductDescription)
class ProductDescriptionAdmin(ModelAdmin):
    list_display = ['product', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['product__name', 'overview', 'ingredients']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Product', {
            'fields': ('product',)
        }),
        ('Description Sections', {
            'fields': ('overview', 'ingredients', 'storage_instructions', 'allergy_info')
        }),
        ('Cake Specific Information', {
            'fields': ('cake_specific_info', 'customization_options'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )