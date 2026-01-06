# apps/payment/models.py - FINAL VERSION
from django.db import models
from django.conf import settings
import uuid

class PaymentTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('initiated', 'Initiated'),
        ('expired', 'Expired'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )
    
    order = models.ForeignKey(
    'orders.Order',
    on_delete=models.CASCADE,  # Use CASCADE instead of SET_NULL
    related_name='payment_transactions'
    # REMOVE null=True, blank=True
)
    
    transaction_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    product_code = models.CharField(max_length=50, default='EPAYTEST')
    
    # Amount details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # eSewa response fields
    esewa_status = models.CharField(max_length=50, blank=True)
    reference_id = models.CharField(max_length=100, blank=True)
    signature = models.CharField(max_length=500, blank=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    esewa_response_data = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        order_num = self.order.order_number if self.order else 'N/A'
        return f"{order_num} - NPR {self.total_amount} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_uuid']),
            models.Index(fields=['order']),
            models.Index(fields=['status']),
            models.Index(fields=['user']),
        ]
        verbose_name = 'Payment Transaction'
        verbose_name_plural = 'Payment Transactions'
    
    # Custom property to get order number
    @property
    def order_number(self):
        return self.order.order_number if self.order else None