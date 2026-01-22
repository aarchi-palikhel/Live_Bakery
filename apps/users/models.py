from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
import secrets
from django.utils import timezone
from datetime import timedelta

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self,username, email, password=None, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        Superusers are always Owners.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'owner')  # Superuser = Owner
        
        # Ensure is_superuser is True for owners
        if extra_fields.get('user_type') == 'owner':
            extra_fields['is_superuser'] = True
        
        return self.create_user(username, email, password, **extra_fields)
    
    def get_by_natural_key(self, username):
        """
        Allow authentication using either username or email
        """
        return self.get(
            models.Q(username__iexact=username) | models.Q(email__iexact=username)
        )

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('customer', 'Customer'),
        ('staff', 'Staff'),
        ('owner', 'Owner/Superuser'),
    )
    
    # Override email field to make it required
    email = models.EmailField(
        _('email address'),
        unique=True,
        help_text=_('Required. Enter a valid email address.')
    )
    
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
    
    user_type = models.CharField(
        _('user type'),
        max_length=10,
        choices=USER_TYPE_CHOICES,
        default='customer'
    )
    
    primary_address = models.TextField(
        _('primary address'),
        blank=True,
        help_text=_('Primary address for staff members')
    )
    
    delivery_address = models.TextField(
        _('delivery address'),
        blank=True,
        help_text=_('Default delivery address for customers')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = CustomUserManager()
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']
    
    def __str__(self):
        return self.username
    
    def save(self, *args, **kwargs):
        """
        Ensure that Owners are always superusers.
        """
        if self.user_type == 'owner':
            self.is_superuser = True
            self.is_staff = True
        
        # Ensure staff are not superusers
        if self.user_type == 'staff':
            self.is_superuser = False
            self.is_staff = True
        
        # Ensure customers are not staff or superusers
        if self.user_type == 'customer':
            self.is_superuser = False
            self.is_staff = False
        
        super().save(*args, **kwargs)
    
    def is_customer(self):
        return self.user_type == 'customer'
    
    def is_staff_member(self):
        return self.user_type == 'staff'
    
    def is_owner(self):
        return self.user_type == 'owner'
    
    @property
    def is_staff(self):
        """
        Override is_staff property to check user_type.
        """
        return self.user_type in ['staff', 'owner']
    
    @is_staff.setter
    def is_staff(self, value):
        """
        Prevent setting is_staff directly - it should be controlled by user_type.
        """
        pass

    def create_remember_token(self):
        """Create a new remember me token for this user"""
        # Clean up old tokens first
        RememberMeToken.objects.filter(user=self).delete()
        
        # Create new token
        token = RememberMeToken.objects.create(
            user=self,
            token=secrets.token_urlsafe(32),
            expires_at=timezone.now() + timedelta(days=14)  # 2 weeks
        )
        return token.token
    
    def get_remember_token(self, token):
        """Get valid remember me token for this user"""
        try:
            token_obj = RememberMeToken.objects.get(
                user=self,
                token=token,
                expires_at__gt=timezone.now()
            )
            return token_obj
        except RememberMeToken.DoesNotExist:
            return None
    
    def clear_remember_tokens(self):
        """Clear all remember me tokens for this user"""
        count = RememberMeToken.objects.filter(user=self).count()
        RememberMeToken.objects.filter(user=self).delete()
        return count


class RememberMeToken(models.Model):
    """Model to store remember me tokens"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='remember_tokens')
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_used = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Remember Me Token'
        verbose_name_plural = 'Remember Me Tokens'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'expires_at']),
        ]
    
    def __str__(self):
        return f"Remember token for {self.user.username}"
    
    def is_valid(self):
        """Check if token is still valid"""
        return timezone.now() < self.expires_at
    
    def use_token(self):
        """Mark token as used and update last_used timestamp"""
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])


# ==================== CUSTOMER CLASS ====================
class CustomerManager(CustomUserManager):
    def get_queryset(self):
        return super().get_queryset().filter(user_type='customer')

class Customer(CustomUser):
    objects = CustomerManager()
    
    class Meta:
        proxy = True
        verbose_name = _('customer')
        verbose_name_plural = _('customers')
    
    def save(self, *args, **kwargs):
        self.user_type = 'customer'
        self.is_superuser = False
        self.is_staff = False
        super().save(*args, **kwargs)

# ==================== STAFF CLASS ====================
class StaffManager(CustomUserManager):
    def get_queryset(self):
        return super().get_queryset().filter(user_type='staff')

class Staff(CustomUser):
    objects = StaffManager()
    
    class Meta:
        proxy = True
        verbose_name = _('staff')
        verbose_name_plural = _('staff members')
    
    def save(self, *args, **kwargs):
        self.user_type = 'staff'
        self.is_superuser = False
        self.is_staff = True
        super().save(*args, **kwargs)

# ==================== OWNER CLASS (SUPERUSER) ====================
class OwnerManager(CustomUserManager):
    def get_queryset(self):
        return super().get_queryset().filter(user_type='owner')

class Owner(CustomUser):
    objects = OwnerManager()
    
    class Meta:
        proxy = True
        verbose_name = _('owner/superuser')
        verbose_name_plural = _('owners/superusers')
    
    def save(self, *args, **kwargs):
        self.user_type = 'owner'
        self.is_superuser = True
        self.is_staff = True
        super().save(*args, **kwargs)