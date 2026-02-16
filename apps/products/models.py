from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.core.validators import MinValueValidator

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('products:product_list_by_category', args=[self.slug])

class Product(models.Model):
    # Cake specific choices
    CAKE_FLAVORS = [
        ('chocolate', 'Chocolate'),
        ('vanilla', 'Vanilla'),
        ('red_velvet', 'Red Velvet'),
        ('black_forest', 'Black Forest'),
        ('butterscotch', 'Butterscotch'),
        ('fruit', 'Fruit Cake'),
        ('cheese', 'Cheese Cake'),
        ('white_forest', 'White Forest'),
        ('custom', 'Custom Flavor'),
    ]
    
    TIER_CHOICES = [
        (1, 'Single Tier'),
        (2, 'Two Tiers'),
        (3, 'Three Tiers'),
    ]
    
    # Weight choices for cakes in pounds
    CAKE_WEIGHT_CHOICES = [
        ('0.5', '0.5 lb'),
        ('1', '1 lb'),
        ('2', '2 lb'),
        ('3', '3 lb'),
        ('4', '4 lb'),
        ('5', '5 lb'),
        ('custom', 'Custom Weight'),
    ]
    
    # Basic product fields
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    short_description = models.CharField(max_length=255, blank=True, help_text="Short description for product cards")
    description = models.TextField(help_text="Detailed description for product detail page")
    
    # Pricing
    base_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Base price for single tier"
    )
    
    # Product status
    available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    in_stock = models.BooleanField(default=True)
    stock_quantity = models.PositiveIntegerField(
        default=0,
        help_text="Available stock quantity. Set to 0 for unlimited stock (cakes/custom orders)"
    )
    
    # Cake specific fields
    is_cake = models.BooleanField(default=False)
    available_flavors = models.CharField(
        max_length=500,
        blank=True,
        help_text="Comma-separated list of available flavors"
    )
    max_tiers = models.IntegerField(choices=TIER_CHOICES, default=1)
    cake_weight = models.CharField(
        max_length=20,
        choices=CAKE_WEIGHT_CHOICES,
        blank=True,
        help_text="Weight in pounds (for cakes only)"
    )
    allow_custom_design = models.BooleanField(default=False)
    allow_reference_image = models.BooleanField(default=True, help_text="Allow customers to upload reference images")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Metadata - For non-cake products
    weight = models.CharField(max_length=50, blank=True, help_text="e.g., 500g, 1kg, 2kg (for non-cake products)")
    
    # Product Images - Direct image fields
    image = models.ImageField(upload_to='products/%Y/%m/%d/', blank=True, null=True, help_text="Main product image")
    image_2 = models.ImageField(upload_to='products/%Y/%m/%d/', blank=True, null=True, help_text="Additional image 2")
    image_3 = models.ImageField(upload_to='products/%Y/%m/%d/', blank=True, null=True, help_text="Additional image 3")
    image_4 = models.ImageField(upload_to='products/%Y/%m/%d/', blank=True, null=True, help_text="Additional image 4")

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['available', 'is_featured']),
            models.Index(fields=['category', 'available']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('products:product_detail', args=[self.id, self.slug])
    
    def get_all_images(self):
        """Return list of all product images"""
        images = []
        if self.image:
            images.append(self.image)
        if self.image_2:
            images.append(self.image_2)
        if self.image_3:
            images.append(self.image_3)
        if self.image_4:
            images.append(self.image_4)
        return images
    
    def get_main_image(self):
        """Return the main product image"""
        return self.image if self.image else None
    
    @property
    def display_price(self):
        """Return formatted price with currency symbol"""
        return f"Rs. {self.base_price}"
    
    @property
    def tier_multipliers(self):
        """Return tier price multipliers"""
        return {
            1: 1.0,    # Single tier - base price
            2: 1.8,    # Two tiers - 1.8x price
            3: 2.5,    # Three tiers - 2.5x price
        }
    
    @property
    def display_weight(self):
        """Display appropriate weight based on product type"""
        if self.is_cake and self.cake_weight:
            return f"{self.get_cake_weight_display()}"
        elif self.weight:
            return self.weight
        return "Weight not specified"
    
    def calculate_price(self, tiers=1):
        """Calculate price based on tiers"""
        multiplier = self.tier_multipliers.get(tiers, 1.0)
        return self.base_price * multiplier

    def get_available_flavors_list(self):
        """Return list of available flavors"""
        if self.available_flavors:
            return [flavor.strip() for flavor in self.available_flavors.split(',')]
        return []
    
    def has_stock(self, quantity=1):
        """Check if product has sufficient stock"""
        # Cakes and custom orders (stock_quantity=0) are always available
        if self.stock_quantity == 0:
            return True
        return self.stock_quantity >= quantity
    
    def reduce_stock(self, quantity):
        """Reduce stock quantity after purchase"""
        if self.stock_quantity > 0:  # Only reduce if tracking stock
            self.stock_quantity -= quantity
            if self.stock_quantity <= 0:
                self.in_stock = False
            self.save()
    
    def increase_stock(self, quantity):
        """Increase stock quantity (for returns/restocking)"""
        if self.stock_quantity >= 0:  # Only increase if tracking stock
            self.stock_quantity += quantity
            if self.stock_quantity > 0:
                self.in_stock = True
            self.save()
    
    @property
    def stock_status(self):
        """Return stock status as string"""
        if self.stock_quantity == 0:
            return "Made to Order"
        elif self.stock_quantity <= 5:
            return f"Low Stock ({self.stock_quantity} left)"
        else:
            return f"In Stock ({self.stock_quantity} available)"
    
    def get_detailed_description(self):
        """Get or create detailed description for the product"""
        if hasattr(self, 'detailed_description'):
            return self.detailed_description
        # Create a default detailed description if none exists
        return ProductDescription.objects.create(
            product=self,
            overview=self.description,
            ingredients="Fresh ingredients used",
            storage_instructions="Store in a cool, dry place",
        )

class ProductDescription(models.Model):
    """Model for detailed product descriptions with sections"""
    product = models.OneToOneField(
        Product, 
        on_delete=models.CASCADE, 
        related_name='detailed_description'
    )
    
    # Main description sections
    overview = models.TextField(
        help_text="Main product overview/description"
    )
    
    ingredients = models.TextField(
        blank=True,
        help_text="List of ingredients"
    )
    
    storage_instructions = models.TextField(
        blank=True,
        help_text="Storage and handling instructions"
    )
    
    allergy_info = models.TextField(
        blank=True,
        help_text="Allergy information"
    )
    
    # For cakes specifically
    cake_specific_info = models.TextField(
        blank=True,
        help_text="Cake-specific information (baking time, shelf life, etc.)"
    )
    
    customization_options = models.TextField(
        blank=True,
        help_text="Available customization options"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Product Detailed Description"
        verbose_name_plural = "Product Detailed Descriptions"
    
    def __str__(self):
        return f"Detailed description for {self.product.name}"
    
    def get_formatted_ingredients(self):
        """Return ingredients as a list"""
        if self.ingredients:
            return [ingredient.strip() for ingredient in self.ingredients.split(',')]
        return []