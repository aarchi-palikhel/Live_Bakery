from django.db import models
from django.utils import timezone

class ContactMessage(models.Model):
    SUBJECT_CHOICES = [
        ('general', 'General Inquiry'),
        ('order', 'Order Inquiry'),
        ('catering', 'Catering Service'),
        ('custom', 'Custom Cake Order'),
        ('feedback', 'Feedback'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('closed', 'Closed'),
    ]

    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Message Details
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES)
    message = models.TextField()
    
    # Meta Information
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='new')
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    replied_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'contact_messages'
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.get_subject_display()} - {self.created_at.strftime('%Y-%m-%d')}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def mark_as_read(self):
        self.status = 'read'
        self.save()

    def mark_as_replied(self):
        self.status = 'replied'
        self.replied_at = timezone.now()
        self.save()

    def get_days_since_creation(self):
        return (timezone.now() - self.created_at).days

    @property
    def has_replies(self):
        return self.replies.exists()

    @property
    def latest_reply(self):
        return self.replies.order_by('-created_at').first()


class ContactMessageReply(models.Model):
    contact_message = models.ForeignKey(
        ContactMessage, 
        on_delete=models.CASCADE, 
        related_name='replies'
    )
    admin_user = models.ForeignKey(
        'users.CustomUser',  # Use string reference to avoid import issues
        on_delete=models.CASCADE,
        limit_choices_to={'user_type__in': ['staff', 'owner']}  # Use user_type instead of is_staff
    )
    reply_message = models.TextField()
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contact_message_replies'
        verbose_name = 'Contact Message Reply'
        verbose_name_plural = 'Contact Message Replies'
        ordering = ['-created_at']

    def __str__(self):
        return f"Reply to {self.contact_message.full_name} by {self.admin_user.username}"

    def send_email(self):
        """Send the reply via email to the customer"""
        from .email_utils import send_contact_reply_email
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # Use the email utility function
            success = send_contact_reply_email(
                contact_message=self.contact_message,
                reply_message=self.reply_message,
                admin_user=self.admin_user
            )
            
            if success:
                # Mark as sent
                self.email_sent = True
                self.email_sent_at = timezone.now()
                self.save()
                
                # Update the original message status
                self.contact_message.mark_as_replied()
                
                logger.info(f"Reply email sent successfully to {self.contact_message.email}")
                return True
            else:
                logger.error(f"Failed to send reply email to {self.contact_message.email}")
                return False
            
        except Exception as e:
            logger.error(f"Error sending reply email to {self.contact_message.email}: {e}")
            return False