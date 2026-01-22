import uuid
from django.db import models
from django.conf import settings
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from products.models import Product
from cart.models import Cart

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('baking', 'Baking'),
        ('ready', 'Ready for Pickup/Delivery'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('esewa', 'eSewa'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Payment Pending'),
        ('paid', 'Paid'),
        ('failed', 'Payment Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]

    DELIVERY_CHOICES = [
        ('delivery', 'Home Delivery'),
        ('pickup', 'Self Pickup'),
    ]

    # Explicit ID field
    id = models.BigAutoField(primary_key=True)
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='orders'
    )
    order_number = models.CharField(max_length=20, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status field
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Delivery fields
    delivery_type = models.CharField(
        max_length=20, 
        choices=DELIVERY_CHOICES, 
        default='delivery'
    )
    delivery_address = models.TextField(blank=True)
    phone_number = models.CharField(max_length=15, blank=True)

    # Financial fields
    subtotal = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0
    )
    
    delivery_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0
    )

    # Payment fields - SINGLE DEFINITION
    payment_method = models.CharField(
        max_length=20, 
        choices=PAYMENT_CHOICES, 
        default='cod'
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )

    payment_transaction = models.ForeignKey(
        'payment.PaymentTransaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    
    special_instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['payment_status', 'status']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['payment_method', 'payment_status']),
        ]
    
    def save(self, *args, **kwargs):
        # SIMPLIFIED save method - only generate order number
        # All calculations should be done in views, not here
        
        # Generate order number if not exists
        if not self.order_number:
            prefix = 'ORD-'
            unique_id = str(uuid.uuid4().hex[:6]).upper()
            self.order_number = f"{prefix}{unique_id}"
        
        # Call parent save without additional logic
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
    def get_payment_status_display_class(self):
        """Return CSS class for payment status display"""
        payment_status_classes = {
            'pending': 'bg-yellow-100 text-yellow-800',
            'paid': 'bg-green-100 text-green-800',
            'failed': 'bg-red-100 text-red-800',
            'refunded': 'bg-gray-100 text-gray-800',
        }
        return payment_status_classes.get(self.payment_status, 'bg-gray-100 text-gray-800')
    
    @property
    def item_count(self):
        """Total number of items in order"""
        return sum(item.quantity for item in self.items.all())
    
    def get_absolute_url(self):
        """Get URL for order detail view"""
        from django.urls import reverse
        return reverse('orders:order_detail', args=[str(self.id)])
    
    def calculate_totals(self):
        """
        Calculate subtotal, delivery fee, and total
        Call this method explicitly when needed, not in save()
        """
        if hasattr(self, 'items'):
            self.subtotal = sum(item.get_total_price() for item in self.items.all())
        else:
            self.subtotal = 0
        
        # Calculate delivery fee if not already set
        if not self.delivery_fee and self.delivery_type == 'delivery':
            # You can implement delivery fee logic here
            # For now, set a default
            self.delivery_fee = 0 if self.delivery_type == 'pickup' else 100
        
        self.total_amount = self.subtotal + self.delivery_fee
        
        # Save with update_fields to avoid recursion
        self.save(update_fields=['subtotal', 'delivery_fee', 'total_amount'])
        
        return self.subtotal, self.delivery_fee, self.total_amount
    
    @property
    def total_price(self):
        """Alias for total_amount for compatibility"""
        return self.total_amount


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
            models.Index(fields=['order', '-created_at']),
        ]
    
    def __str__(self):
        return f"OrderItem #{self.id} - {self.quantity} x {self.product.name}"
    
    def get_total_price(self):
        return self.price * self.quantity
    
    @property
    def total_price(self):
        """Property alias for get_total_price() for compatibility"""
        return self.get_total_price()
    
    @property
    def is_cake(self):
        """Check if this order item is a cake"""
        return self.product.is_cake
    
    @property
    def display_flavor(self):
        """Display cake flavor with custom flavor if applicable"""
        if self.cake_flavor == 'custom' and self.cake_custom_flavor:
            return f"Custom: {self.cake_custom_flavor}"
        return self.cake_flavor if self.cake_flavor else "Not specified"
    
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



    """
    A utility class for calculating revenue and statistics from successful orders
    (orders with payment_status = 'paid' AND status in ['confirmed', 'completed', 'baking'])
    """
    
    @classmethod
    def get_successful_orders(cls, start_date=None, end_date=None):
        """
        Get all successful orders 
        (payment_status = 'paid' AND status in ['confirmed', 'completed', 'baking'])
        """
        queryset = Order.objects.filter(
            payment_status='paid',
            status__in=['confirmed', 'completed', 'baking']
        )
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            # Add one day to include the end date fully
            end_date = end_date.replace(hour=23, minute=59, second=59)
            queryset = queryset.filter(created_at__lte=end_date)
            
        return queryset
    
    @classmethod
    def calculate_total_revenue(cls, start_date=None, end_date=None):
        """
        Calculate total revenue from successful orders
        """
        successful_orders = cls.get_successful_orders(start_date, end_date)
        total = successful_orders.aggregate(total_revenue=Sum('total_amount'))
        return total['total_revenue'] or 0
    
    @classmethod
    def calculate_average_order_value(cls, start_date=None, end_date=None):
        """
        Calculate average order value from successful orders
        """
        successful_orders = cls.get_successful_orders(start_date, end_date)
        result = successful_orders.aggregate(
            avg_value=Avg('total_amount'),
            count=Count('id')
        )
        
        if result['count'] > 0:
            return result['avg_value'] or 0
        return 0
    
    @classmethod
    def get_order_count(cls, start_date=None, end_date=None):
        """
        Get count of successful orders
        """
        successful_orders = cls.get_successful_orders(start_date, end_date)
        return successful_orders.count()
    
    @classmethod
    def get_revenue_by_date_range(cls, days=30):
        """
        Get revenue breakdown by date for the last N days
        """
        end_date = timezone.now()
        start_date = end_date - timezone.timedelta(days=days)
        
        # Get daily revenue
        orders = cls.get_successful_orders(start_date, end_date)
        daily_revenue = {}
        
        for order in orders:
            date_str = order.created_at.strftime('%Y-%m-%d')
            if date_str not in daily_revenue:
                daily_revenue[date_str] = 0
            daily_revenue[date_str] += float(order.total_amount)
        
        return daily_revenue
    
    @classmethod
    def get_top_products(cls, start_date=None, end_date=None, limit=10):
        """
        Get top selling products from successful orders
        """
        successful_orders = cls.get_successful_orders(start_date, end_date)
        
        # Get order items from successful orders
        order_items = OrderItem.objects.filter(
            order__in=successful_orders
        ).select_related('product')
        
        # Aggregate product sales
        product_sales = {}
        
        for item in order_items:
            product_id = item.product.id
            product_name = item.product.name
            
            if product_id not in product_sales:
                product_sales[product_id] = {
                    'name': product_name,
                    'quantity_sold': 0,
                    'revenue': 0,
                    'orders': set()
                }
            
            product_sales[product_id]['quantity_sold'] += item.quantity
            product_sales[product_id]['revenue'] += float(item.total_price)
            product_sales[product_id]['orders'].add(item.order_id)
        
        # Convert to list and calculate orders count
        result = []
        for product_id, data in product_sales.items():
            result.append({
                'product_id': product_id,
                'product_name': data['name'],
                'quantity_sold': data['quantity_sold'],
                'revenue': data['revenue'],
                'orders_count': len(data['orders'])
            })
        
        # Sort by revenue (descending) and limit
        result.sort(key=lambda x: x['revenue'], reverse=True)
        return result[:limit]
    
    @classmethod
    def get_summary_report(cls, start_date=None, end_date=None):
        """
        Get a comprehensive summary report of successful orders
        """
        successful_orders = cls.get_successful_orders(start_date, end_date)
        
        if not successful_orders.exists():
            return {
                'total_revenue': 0,
                'order_count': 0,
                'average_order_value': 0,
                'total_items_sold': 0,
                'delivery_types': {'delivery': 0, 'pickup': 0},
                'payment_methods': {'cod': 0, 'esewa': 0}
            }
        
        # Calculate basic metrics
        total_revenue = cls.calculate_total_revenue(start_date, end_date)
        order_count = cls.get_order_count(start_date, end_date)
        avg_order_value = cls.calculate_average_order_value(start_date, end_date)
        
        # Get total items sold
        order_items = OrderItem.objects.filter(order__in=successful_orders)
        total_items_sold = order_items.aggregate(total_quantity=Sum('quantity'))
        total_items_sold = total_items_sold['total_quantity'] or 0
        
        # Analyze delivery types
        delivery_types = successful_orders.values('delivery_type').annotate(
            count=Count('id')
        )
        delivery_type_dict = {item['delivery_type']: item['count'] for item in delivery_types}
        
        # Analyze payment methods
        payment_methods = successful_orders.values('payment_method').annotate(
            count=Count('id')
        )
        payment_method_dict = {item['payment_method']: item['count'] for item in payment_methods}
        
        return {
            'total_revenue': float(total_revenue),
            'order_count': order_count,
            'average_order_value': float(avg_order_value),
            'total_items_sold': total_items_sold,
            'delivery_types': delivery_type_dict,
            'payment_methods': payment_method_dict,
            'date_range': {
                'start_date': start_date,
                'end_date': end_date
            }
        }
class CakeCustomization(models.Model):
    """Model for storing cake customization details"""
    
    id = models.BigAutoField(primary_key=True)
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cake_customizations'
    )
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='customizations'
    )
    
    # Customization fields
    cake_flavor = models.CharField(max_length=100, blank=True)
    cake_custom_flavor = models.CharField(max_length=200, blank=True)
    cake_weight = models.CharField(max_length=50, blank=True)
    cake_custom_weight = models.CharField(max_length=50, blank=True)
    cake_tiers = models.IntegerField(default=1)
    message_on_cake = models.CharField(max_length=100, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    special_instructions = models.TextField(blank=True)
    
    # Reference image
    reference_image = models.ImageField(
        upload_to='cake_designs/%Y/%m/%d/',
        null=True,
        blank=True
    )
    reference_title = models.CharField(max_length=200, blank=True)
    reference_description = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Cake Customization'
        verbose_name_plural = 'Cake Customizations'
    
    def __str__(self):
        return f"Customization #{self.id} - {self.product.name}"
    
    @property
    def display_weight(self):
        """Display cake weight with custom weight if applicable"""
        if self.cake_weight == 'custom' and self.cake_custom_weight:
            return f"Custom: {self.cake_custom_weight} lb"
        return self.cake_weight + " lb" if self.cake_weight else "Not specified"