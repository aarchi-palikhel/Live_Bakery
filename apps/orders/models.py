import uuid
from django.db import models
from django.conf import settings
from products.models import Product
from cart.models import Cart

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('baking', 'Baking'),
        ('ready', 'Ready for Pickup'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('online', 'Online Payment'),
    ]
    
    # Explicit ID field (optional, Django creates it automatically)
    id = models.BigAutoField(primary_key=True)
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='orders'
    )
    order_number = models.CharField(max_length=20, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cod')
    payment_status = models.BooleanField(default=False)
    special_instructions = models.TextField(blank=True)
    delivery_address = models.TextField(blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate a unique order number like ORD-XXXXXX
            prefix = 'ORD-'
            unique_id = str(uuid.uuid4().hex[:6]).upper()
            self.order_number = f"{prefix}{unique_id}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Order #{self.id} - {self.order_number} - {self.user.username}"
    
    @property
    def get_status_display_class(self):
        """Return CSS class for status display"""
        status_classes = {
            'pending': 'bg-yellow-100 text-yellow-800',
            'confirmed': 'bg-blue-100 text-blue-800',
            'baking': 'bg-purple-100 text-purple-800',
            'ready': 'bg-green-100 text-green-800',
            'completed': 'bg-gray-100 text-gray-800',
            'cancelled': 'bg-red-100 text-red-800',
        }
        return status_classes.get(self.status, 'bg-gray-100 text-gray-800')
    
    @property
    def item_count(self):
        """Total number of items in order"""
        return sum(item.quantity for item in self.items.all())
    
    def get_absolute_url(self):
        """Get URL for order detail view"""
        from django.urls import reverse
        return reverse('orders:order_detail', args=[str(self.id)])

class OrderItem(models.Model):
    # Explicit ID field
    id = models.BigAutoField(primary_key=True)
    
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Cake customization fields (for cake products only)
    cake_flavor = models.CharField(max_length=100, blank=True)
    cake_custom_flavor = models.CharField(max_length=200, blank=True, help_text="If flavor is 'custom'")
    cake_weight = models.CharField(max_length=50, blank=True)
    cake_custom_weight = models.CharField(max_length=50, blank=True, help_text="If weight is 'custom'")
    cake_tiers = models.IntegerField(default=1)
    message_on_cake = models.CharField(max_length=100, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    special_instructions = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
        indexes = [
            models.Index(fields=['order', 'product']),
        ]
    
    def __str__(self):
        return f"OrderItem #{self.id} - {self.quantity} x {self.product.name}"
    
    @property
    def total_price(self):
        return self.price * self.quantity
    
    @property
    def is_cake(self):
        """Check if this order item is a cake"""
        return self.product.is_cake
    
    @property
    def display_flavor(self):
        """Display cake flavor with custom flavor if applicable"""
        if self.cake_flavor == 'custom' and self.cake_custom_flavor:
            return f"Custom: {self.cake_custom_flavor}"
        return self.get_cake_flavor_display() if self.cake_flavor else "Not specified"
    
    @property
    def display_weight(self):
        """Display cake weight with custom weight if applicable"""
        if self.cake_weight == 'custom' and self.cake_custom_weight:
            return f"Custom: {self.cake_custom_weight} lb"
        return self.cake_weight + " lb" if self.cake_weight else "Not specified"

class CakeDesignReference(models.Model):
    """Model for cake design reference images uploaded by customers"""
    
    # Explicit ID field
    id = models.BigAutoField(primary_key=True)
    
    # Direct reference to Order for easy access in admin
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='design_references',
        null=True,
        blank=True,
        help_text="Parent order for this design reference"
    )
    
    # Reference to specific order item
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name='design_references',
        null=True,
        blank=True,
        help_text="Specific order item (cake) for this design"
    )
    
    image = models.ImageField(
        upload_to='cake_designs/%Y/%m/%d/',
        help_text="Reference image for cake design"
    )
    
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Title/name for this design reference"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the desired design"
    )
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Cake Design Reference'
        verbose_name_plural = 'Cake Design References'
        indexes = [
            models.Index(fields=['order', 'order_item']),
            models.Index(fields=['uploaded_at']),
        ]
    
    def __str__(self):
        if self.order and self.order_item:
            return f"Design #{self.id} for Order #{self.order.id} - {self.order_item.product.name}"
        elif self.order:
            return f"Design #{self.id} for Order #{self.order.id}"
        else:
            return f"Design Reference #{self.id}: {self.title or 'Untitled'}"
    
    def save(self, *args, **kwargs):
        """Automatically set order from order_item if not provided"""
        if self.order_item and not self.order:
            self.order = self.order_item.order
        super().save(*args, **kwargs)
    
    @property
    def display_order_info(self):
        """Display order information for admin"""
        if self.order:
            return f"Order #{self.order.id} ({self.order.order_number})"
        return "No order associated"
    
    @property
    def display_product_info(self):
        """Display product information for admin"""
        if self.order_item:
            return f"{self.order_item.product.name} (Qty: {self.order_item.quantity})"
        return "No product associated"