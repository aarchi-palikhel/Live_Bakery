from django import forms
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import Order, CakeDesignReference
import json
from datetime import datetime

class OrderCreateForm(forms.ModelForm):
    """Form for creating a new order from cart"""
    delivery_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-amber-500',
            'placeholder': 'Enter your complete delivery address'
        }),
        required=True
    )
    
    phone_number = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-amber-500',
            'placeholder': 'Enter your phone number'
        }),
        required=True
    )
    
    special_instructions = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-amber-500',
            'placeholder': 'Any special instructions for your order...'
        }),
        required=False
    )
    
    # FIX: Change to use RadioSelect widget with proper rendering
    PAYMENT_CHOICES = [
        ('cod', 'Cash on Delivery (COD)'),
        ('online', 'Pay with eSewa'),
    ]
    
    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.RadioSelect(),
        initial='cod',
        required=True
    )
    
    class Meta:
        model = Order
        fields = ['delivery_address', 'phone_number', 'special_instructions', 'payment_method']
    
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        # Remove any non-digit characters
        phone_number = ''.join(filter(str.isdigit, phone_number))
        
        # Nepal phone number validation (adjust for your country)
        if len(phone_number) != 10:
            raise forms.ValidationError("Please enter a valid 10-digit phone number")
        
        # Check if it starts with valid Nepal prefixes
        valid_prefixes = ['98', '97', '96', '95']
        if not any(phone_number.startswith(prefix) for prefix in valid_prefixes):
            raise forms.ValidationError("Please enter a valid Nepal mobile number")
        
        return phone_number
    
    def clean_delivery_address(self):
        address = self.cleaned_data.get('delivery_address')
        if len(address.strip()) < 10:
            raise forms.ValidationError("Please provide a more detailed delivery address")
        return address


class CakeCustomizationForm(forms.Form):
    # Tier choices
    TIER_CHOICES = [
        (1, 'Single Tier'),
        (2, 'Two Tiers'),
        (3, 'Three Tiers'),
    ]
    
    # Weight choices for cakes in pounds
    CAKE_WEIGHT_CHOICES = [
        ('0.5', '0.5 lb (Serves 2-3)'),
        ('1', '1 lb (Serves 4-6)'),
        ('2', '2 lb (Serves 8-10)'),
        ('3', '3 lb (Serves 12-15)'),
        ('4', '4 lb (Serves 16-20)'),
        ('5', '5 lb (Serves 20-25)'),
        ('custom', 'Custom Weight'),
    ]
    
    def __init__(self, *args, **kwargs):
        product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
    
    # Required Fields
    weight = forms.ChoiceField(
        label="Cake Weight",
        choices=CAKE_WEIGHT_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'space-y-2'}),
        required=True
    )
    
    custom_weight = forms.CharField(
        label="Custom Weight (in pounds)",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., 6',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 mt-2',
        }),
        help_text="Enter weight in pounds (e.g., 6 for 6 lb)"
    )
    
    tiers = forms.ChoiceField(
        label="Number of Tiers",
        choices=TIER_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'flex space-x-4'}),
        required=True,
        initial=1
    )
    
    message_on_cake = forms.CharField(
        label="Message on Cake (Optional)",
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., Happy Birthday!',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
        }),
        help_text="Maximum 50 characters"
    )
    
    # Reference Image Upload
    reference_image = forms.ImageField(
        label="Upload Reference Image (Optional)",
        required=False,
        help_text="Upload a photo of the cake design you want (max 5MB)",
        widget=forms.FileInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100',
            'accept': 'image/*'
        })
    )
    
    reference_title = forms.CharField(
        label="Reference Title (Optional)",
        required=False,
        max_length=200,
        help_text="Give a title to your reference image",
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., Birthday Cake with Blue Theme',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
        })
    )
    
    reference_description = forms.CharField(
        label="Reference Description (Optional)",
        required=False,
        help_text="Describe what you want in the cake design",
        widget=forms.Textarea(attrs={
            'placeholder': 'Describe elements you want: colors, decorations, theme, etc.',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
            'rows': 3
        })
    )
    
    # CHANGE: Use CharField instead of DateField to avoid date object
    delivery_date = forms.CharField(
        label="Delivery Date",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
            'min': (timezone.now() + timezone.timedelta(days=2)).date().isoformat(),
        }),
        required=True,
        help_text="Please allow at least 2 days for preparation"
    )
    
    quantity = forms.IntegerField(
        label="Quantity",
        min_value=1,
        max_value=10,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
        }),
        required=True,
        validators=[
            MinValueValidator(1, message="Quantity must be at least 1"),
            MaxValueValidator(10, message="Maximum 10 cakes per order")
        ]
    )
    
    special_instructions = forms.CharField(
        label="Special Instructions (Optional)",
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': 'Any special requirements, allergies, or instructions...',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
            'rows': 3
        })
    )
    
    def clean_delivery_date(self):
        date_str = self.cleaned_data.get('delivery_date')
        today = timezone.now().date()
        
        if not date_str:
            raise forms.ValidationError("Please select a delivery date.")
        
        try:
            # Parse the string date
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            raise forms.ValidationError("Please enter a valid date in YYYY-MM-DD format.")
        
        if date < today:
            raise forms.ValidationError("Delivery date cannot be in the past.")
        
        # Require at least 2 days notice for cake orders
        min_date = today + timezone.timedelta(days=2)
        if date < min_date:
            raise forms.ValidationError("Please allow at least 2 days for cake preparation.")
        
        # Don't allow orders too far in advance (optional)
        max_date = today + timezone.timedelta(days=30)
        if date > max_date:
            raise forms.ValidationError("Orders can only be placed up to 30 days in advance.")
        
        # Return the date object (for database storage) AND keep the string
        self.delivery_date_obj = date  # Store date object as instance attribute
        return date_str  # Return string for session storage
    
    def clean_custom_weight(self):
        custom_weight = self.cleaned_data.get('custom_weight')
        weight = self.cleaned_data.get('weight')
        
        if weight == 'custom' and custom_weight:
            try:
                # Try to parse as float
                weight_value = float(custom_weight)
                if weight_value <= 0:
                    raise forms.ValidationError("Weight must be greater than 0")
                if weight_value > 20:  # Maximum 20 lb
                    raise forms.ValidationError("Maximum weight is 20 lb for custom orders")
                return str(weight_value)
            except ValueError:
                raise forms.ValidationError("Please enter a valid number for weight")
        
        return custom_weight
    
    def clean(self):
        cleaned_data = super().clean()
        weight = cleaned_data.get('weight')
        custom_weight = cleaned_data.get('custom_weight')
        reference_image = cleaned_data.get('reference_image')
        reference_title = cleaned_data.get('reference_title')
        
        # Validate custom weight
        if weight == 'custom' and not custom_weight:
            self.add_error('custom_weight', 'Please specify custom weight')
        
        # Validate reference image has title if provided
        if reference_image and not reference_title:
            self.add_error('reference_title', 'Please provide a title for your reference image')
        
        # Validate image size (optional)
        if reference_image:
            max_size = 5 * 1024 * 1024  # 5MB
            if reference_image.size > max_size:
                self.add_error('reference_image', 'Image size should not exceed 5MB')
        
        return cleaned_data
    
    def get_session_data(self):
        """
        Get all form data as JSON-serializable dictionary for session storage.
        This ensures all data can be safely stored in session.
        """
        if not self.is_valid():
            return None
        
        # Create a clean copy of cleaned_data
        session_data = {}
        
        for key, value in self.cleaned_data.items():
            if key == 'delivery_date':
                # Already a string from clean_delivery_date()
                session_data[key] = value
            elif key == 'reference_image':
                # Store only the filename
                session_data[key] = value.name if value else None
            elif hasattr(value, 'isoformat'):
                # Convert any other date/datetime objects to string
                session_data[key] = value.isoformat()
            else:
                # All other data types are JSON serializable
                session_data[key] = value
        
        # Add additional data if needed
        session_data['quantity'] = self.cleaned_data.get('quantity', 1)
        
        return session_data
    
    def save_design_reference(self, order_item):
        """Save the cake design reference if image was uploaded"""
        reference_image = self.cleaned_data.get('reference_image')
        reference_title = self.cleaned_data.get('reference_title')
        reference_description = self.cleaned_data.get('reference_description')
        
        if reference_image:
            design_reference = CakeDesignReference(
                order_item=order_item,
                image=reference_image,
                title=reference_title or f"Design for {order_item.product.name}",
                description=reference_description or f"Custom cake order",
            )
            design_reference.save()
            return design_reference
        return None
    
    def get_cake_customization_data(self):
        """Extract cake customization data for order item"""
        data = {
            'cake_weight': self.cleaned_data.get('weight'),
            'cake_custom_weight': self.cleaned_data.get('custom_weight'),
            'cake_tiers': self.cleaned_data.get('tiers'),
            'message_on_cake': self.cleaned_data.get('message_on_cake'),
            'special_instructions': self.cleaned_data.get('special_instructions'),
        }
        
        # Use the date object if available, otherwise use the string
        if hasattr(self, 'delivery_date_obj'):
            data['delivery_date'] = self.delivery_date_obj
        else:
            # Try to parse the string date
            date_str = self.cleaned_data.get('delivery_date')
            if date_str:
                try:
                    data['delivery_date'] = datetime.strptime(date_str, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    data['delivery_date'] = None
        
        return data