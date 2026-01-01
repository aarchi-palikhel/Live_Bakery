from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, email, password, **extra_fields)

class CustomUser(AbstractUser):
    # User type choices
    USER_TYPE_CHOICES = (
        ('customer', 'Customer'),
        ('admin', 'Admin'),
    )
    
    # Phone number field
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+9779841234567'. Up to 15 digits allowed."
    )
    
    mobile_no = models.CharField(
        _('mobile number'),
        validators=[phone_regex],
        max_length=17,
        blank=True
    )
    
    # User type field
    user_type = models.CharField(
        _('user type'),
        max_length=10,
        choices=USER_TYPE_CHOICES,
        default='customer'
    )
    
    # Main address field (simple)
    address = models.TextField(
        _('address'),
        blank=True,
        help_text=_('Primary delivery address')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = CustomUserManager()
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']
    
    def __str__(self):
        return self.username
    
    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()
    
    def is_customer_user(self):
        return not self.is_staff
    
    def is_admin_user(self):
        return self.is_staff

class CustomerManager(CustomUserManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_staff=False)

class Customer(CustomUser):
    objects = CustomerManager()
    
    class Meta:
        proxy = True
        verbose_name = _('customer')
        verbose_name_plural = _('customers')
    
    def save(self, *args, **kwargs):
        # Ensure customer is never staff or superuser
        self.is_staff = False
        self.is_superuser = False
        self.user_type = 'customer'
        super().save(*args, **kwargs)

class AdminManager(CustomUserManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_staff=True)

class Admin(CustomUser):
    objects = AdminManager()
    
    class Meta:
        proxy = True
        verbose_name = _('admin')
        verbose_name_plural = _('admins')
    
    def save(self, *args, **kwargs):
        # Ensure admin is always staff
        self.is_staff = True
        self.user_type = 'admin'
        super().save(*args, **kwargs)

class Address(models.Model):
    """
    Multiple addresses for customers (home, work, etc.)
    """
    ADDRESS_TYPES = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='addresses',
        null=True,  # Allow null during migration
        blank=True  # Allow blank during migration
    )
    
    address_type = models.CharField(
        _('address type'),
        max_length=10,
        choices=ADDRESS_TYPES,
        default='home'
    )
    
    street_address = models.CharField(
        _('street address'),
        max_length=255
    )
    
    city = models.CharField(
        _('city'),
        max_length=100,
        default='Bhaktapur'
    )
    
    municipality = models.CharField(
        _('municipality'),
        max_length=100,
        default='Kamalbinayak'
    )
    
    ward_number = models.PositiveSmallIntegerField(
        _('ward number'),
        null=True,
        blank=True
    )
    
    # Nepal-specific address fields
    tole = models.CharField(
        _('tole'),
        max_length=100,
        blank=True,
        help_text=_('Neighborhood or area name')
    )
    
    landmark = models.CharField(
        _('landmark'),
        max_length=200,
        blank=True,
        help_text=_('Nearby landmark for delivery')
    )
    
    is_default = models.BooleanField(
        _('default address'),
        default=False,
        help_text=_('Use this as the default delivery address')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('address')
        verbose_name_plural = _('addresses')
        ordering = ['-is_default', 'address_type']
    
    def __str__(self):
        return f"{self.get_address_type_display()} - {self.street_address}, {self.city}"
    
    def get_full_address(self):
        """Return formatted full address"""
        address_parts = [self.street_address]
        if self.tole:
            address_parts.append(self.tole)
        if self.landmark:
            address_parts.append(f"Near {self.landmark}")
        address_parts.extend([self.municipality, self.city])
        
        if self.ward_number:
            address_parts.append(f"Ward {self.ward_number}")
            
        return ", ".join(filter(None, address_parts))