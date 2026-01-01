# admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, ProductImage, ProductDescription

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ['preview_image']
    fields = ['image', 'preview_image', 'alt_text', 'is_default', 'display_order']
    
    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="60" height="60" style="object-fit: cover; border-radius: 5px;" />', obj.image.url)
        return "-"
    preview_image.short_description = "Preview"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
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
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'display_price', 'display_image', 'available', 'is_featured', 'is_cake', 'in_stock', 'created_at']
    list_filter = ['category', 'available', 'is_featured', 'is_cake', 'in_stock', 'created_at']
    search_fields = ['name', 'short_description', 'description', 'category__name']
    list_editable = ['available', 'is_featured', 'is_cake', 'in_stock']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'preview_image', 'display_weight']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'category', 'short_description', 'description')
        }),
        ('Pricing & Availability', {
            'fields': ('base_price', 'available', 'in_stock', 'is_featured')
        }),
        ('Product Details', {
            'fields': ('weight', 'display_weight')
        }),
        ('Cake Specific Options', {
            'fields': ('is_cake', 'available_flavors', 'max_tiers', 'cake_weight', 'allow_custom_design', 'allow_reference_image'),
            'classes': ('collapse',)
        }),
        ('Main Image', {
            'fields': ('preview_image',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def display_price(self, obj):
        return f"Rs. {obj.base_price}"
    display_price.short_description = "Price"
    
    def display_image(self, obj):
        # Try to get first product image
        if obj.images.filter(is_default=True).exists():
            image = obj.images.filter(is_default=True).first()
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />', image.image.url)
        return "-"
    display_image.short_description = "Image"
    
    def preview_image(self, obj):
        # Show main image if exists
        if obj.images.filter(is_default=True).exists():
            image = obj.images.filter(is_default=True).first()
            return format_html('<img src="{}" width="200" height="200" style="object-fit: cover; border-radius: 10px;" />', image.image.url)
        return "No default image set. Upload images in the Product Images section below."
    preview_image.short_description = "Image Preview"

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'preview_image', 'alt_text', 'is_default', 'display_order', 'created_at']
    list_filter = ['is_default', 'created_at']
    search_fields = ['product__name', 'alt_text']
    list_editable = ['is_default', 'display_order', 'alt_text']
    readonly_fields = ['created_at', 'preview_image_large']
    
    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />', obj.image.url)
        return "-"
    preview_image.short_description = "Preview"
    
    def preview_image_large(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="300" height="300" style="object-fit: cover; border-radius: 10px;" />', obj.image.url)
        return "No image uploaded"
    preview_image_large.short_description = "Large Preview"

@admin.register(ProductDescription)
class ProductDescriptionAdmin(admin.ModelAdmin):
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