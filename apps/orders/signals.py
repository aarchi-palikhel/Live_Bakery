from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.cache import cache
from .models import Order
from apps.core.email_utils import send_order_status_update_email
import logging

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Order)
def store_old_status(sender, instance, **kwargs):
    """
    Store the old status before saving to detect changes
    """
    if instance.pk:  # Only for existing orders
        try:
            old_order = Order.objects.get(pk=instance.pk)
            # Store old status in cache temporarily
            cache.set(f'order_old_status_{instance.pk}', old_order.status, timeout=60)
        except Order.DoesNotExist:
            pass

@receiver(post_save, sender=Order)
def send_status_update_email(sender, instance, created, **kwargs):
    """
    Send email notification when order status changes
    """
    if created:
        # Don't send email for newly created orders (they start as 'pending')
        return
    
    # Get old status from cache
    old_status = cache.get(f'order_old_status_{instance.pk}')
    
    if old_status and old_status != instance.status:
        # Status has changed, send email notification
        logger.info(f"Order {instance.id} status changed from {old_status} to {instance.status}")
        
        try:
            email_sent = send_order_status_update_email(instance, old_status)
            if email_sent:
                logger.info(f"Status update email sent for order {instance.id} to {instance.user.email}")
            else:
                logger.warning(f"Failed to send status update email for order {instance.id}")
        except Exception as e:
            logger.error(f"Error sending status update email for order {instance.id}: {e}")
        
        # Clean up cache
        cache.delete(f'order_old_status_{instance.pk}')
    elif old_status:
        # Clean up cache even if status didn't change
        cache.delete(f'order_old_status_{instance.pk}')