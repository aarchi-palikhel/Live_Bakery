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