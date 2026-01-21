from django.db import models
from django.conf import settings
from products.models import Product  

class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']  
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'

    def __str__(self):
        return f"Cart of {self.user.username}"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='cart_items'  
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    
    # Foreign key to cake customization (optional - only for cake products)
    cake_customization = models.ForeignKey(
        'orders.CakeCustomization',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cart_items'
    )

    class Meta:
        ordering = ['-added_at']  
        # CHANGED: Only require unique together for non-null cake_customization
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'product', 'cake_customization'],
                name='unique_cart_product_customization',
                condition=models.Q(cake_customization__isnull=False)
            ),
            models.UniqueConstraint(
                fields=['cart', 'product'],
                name='unique_cart_product',
                condition=models.Q(cake_customization__isnull=True)
            ),
        ]
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'

    def __str__(self):
        if self.cake_customization:
            return f"{self.quantity} x {self.product.name} (Customized)"
        return f"{self.quantity} x {self.product.name}"

    @property
    def total_price(self):
        try:
            price = float(self.product.base_price)
            return price * self.quantity
        except (ValueError, AttributeError, TypeError):
            return 0