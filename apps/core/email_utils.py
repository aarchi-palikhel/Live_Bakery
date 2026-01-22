"""
Email utilities for Live Bakery
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def get_from_email():
    """Get the configured from email address"""
    return (
        getattr(settings, 'DEFAULT_FROM_EMAIL', None) or
        getattr(settings, 'EMAIL_HOST_USER', None) or
        'noreply@livebakery.com'
    )


def send_template_email(
    to_email,
    subject,
    template_name,
    context=None,
    from_email=None,
    fail_silently=False
):
    """
    Send an email using a template
    
    Args:
        to_email (str or list): Recipient email address(es)
        subject (str): Email subject
        template_name (str): Template path (without .html extension)
        context (dict): Template context variables
        from_email (str): Sender email (optional, uses default if not provided)
        fail_silently (bool): Whether to suppress exceptions
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if context is None:
        context = {}
    
    if from_email is None:
        from_email = get_from_email()
    
    if isinstance(to_email, str):
        to_email = [to_email]
    
    try:
        # Render HTML template
        html_message = render_to_string(f'{template_name}.html', context)
        
        # Create plain text version
        plain_message = strip_tags(html_message)
        
        logger.info(f"Sending email to {to_email} with subject: {subject}")
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=to_email,
            html_message=html_message,
            fail_silently=fail_silently,
        )
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {e}")
        if not fail_silently:
            raise
        return False


def send_contact_reply_email(contact_message, reply_message, admin_user):
    """
    Send a reply email for a contact message
    
    Args:
        contact_message: ContactMessage instance
        reply_message (str): The reply message content
        admin_user: User instance of the admin sending the reply
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    context = {
        'customer_name': contact_message.full_name,
        'original_message': contact_message.message,
        'reply_message': reply_message,
        'admin_name': admin_user.get_full_name() or admin_user.username,
        'bakery_name': 'Live Bakery',
        'bakery_location': 'Kamalbinayak, Bhaktapur',
        'contact_subject': contact_message.get_subject_display(),
    }
    
    subject = f"Re: {contact_message.get_subject_display()} - Live Bakery"
    
    return send_template_email(
        to_email=contact_message.email,
        subject=subject,
        template_name='emails/contact_reply',
        context=context,
        fail_silently=False
    )


def send_order_confirmation_email(order):
    """
    Send order confirmation email
    
    Args:
        order: Order instance
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not order.user or not order.user.email:
        logger.warning(f"Cannot send order confirmation for order {order.id}: No user email")
        return False
    
    context = {
        'order': order,
        'customer_name': order.user.get_full_name() or order.user.username,
        'bakery_name': 'Live Bakery',
        'bakery_location': 'Kamalbinayak, Bhaktapur',
    }
    
    subject = f"Order Confirmation #{order.order_number} - Live Bakery"
    
    return send_template_email(
        to_email=order.user.email,
        subject=subject,
        template_name='emails/order_confirmation',
        context=context,
        fail_silently=True  # Don't break order process if email fails
    )


def send_welcome_email(user):
    """
    Send welcome email to new users
    
    Args:
        user: User instance
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not user.email:
        logger.warning(f"Cannot send welcome email to user {user.username}: No email address")
        return False
    
    context = {
        'user': user,
        'customer_name': user.get_full_name() or user.username,
        'bakery_name': 'Live Bakery',
        'bakery_location': 'Kamalbinayak, Bhaktapur',
    }
    
    subject = "Welcome to Live Bakery!"
    
    return send_template_email(
        to_email=user.email,
        subject=subject,
        template_name='emails/welcome',
        context=context,
        fail_silently=True
    )


def send_order_status_update_email(order, old_status=None):
    """
    Send order status update email to customer
    
    Args:
        order: Order instance
        old_status: Previous status (optional, for logging)
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not order.user or not order.user.email or not order.user.email.strip():
        logger.warning(f"Cannot send order status update for order {order.id}: No user email")
        return False
    
    # Define status-specific subject lines
    status_subjects = {
        'confirmed': f"Order Confirmed #{order.order_number} - {order.get_status_display()}",
        'baking': f"Order Update #{order.order_number} - Your Order is Being Prepared",
        'ready': f"Order Ready #{order.order_number} - Ready for {order.get_delivery_type_display()}",
        'completed': f"Order Completed #{order.order_number} - Thank You!",
        'cancelled': f"Order Cancelled #{order.order_number} - We're Sorry",
    }
    
    subject = status_subjects.get(
        order.status, 
        f"Order Update #{order.order_number} - {order.get_status_display()}"
    )
    
    context = {
        'order': order,
        'customer_name': order.user.get_full_name() or order.user.username,
        'bakery_name': 'Live Bakery',
        'bakery_location': 'Kamalbinayak, Bhaktapur',
        'old_status': old_status,
        'status_changed': old_status != order.status if old_status else True,
    }
    
    return send_template_email(
        to_email=order.user.email,
        subject=subject,
        template_name='emails/order_status_update',
        context=context,
        fail_silently=True  # Don't break order process if email fails
    )


def test_email_configuration(test_email=None):
    """
    Test the email configuration
    
    Args:
        test_email (str): Email address to send test email to
    
    Returns:
        bool: True if test email was sent successfully, False otherwise
    """
    if not test_email:
        test_email = get_from_email()
    
    context = {
        'bakery_name': 'Live Bakery',
        'test_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    subject = "Live Bakery - Email Configuration Test"
    
    try:
        return send_template_email(
            to_email=test_email,
            subject=subject,
            template_name='emails/test_email',
            context=context,
            fail_silently=False
        )
    except Exception as e:
        logger.error(f"Email configuration test failed: {e}")
        return False