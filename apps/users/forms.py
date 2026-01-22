from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Customer

User = get_user_model()

class CustomerCreationForm(UserCreationForm):
    
    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#8f3232]',
            'placeholder': 'Enter your first name'
        })
    )
    last_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#8f3232]',
            'placeholder': 'Enter your last name'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#8f3232]',
            'placeholder': 'Enter your email address'
        })
    )
    mobile_no = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#8f3232]',
            'placeholder': 'Optional: +9779841234567'
        })
    )
    delivery_address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#8f3232]',
            'placeholder': 'Enter your delivery address (optional)',
            'rows': 3
        })
    )

    class Meta:
        model = Customer
        fields = ['username', 'first_name', 'last_name', 'email', 'mobile_no', 'delivery_address', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Tailwind classes to remaining fields
        self.fields['username'].widget.attrs.update({
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#8f3232]',
            'placeholder': 'Enter your username'
        })
        
        # Remove help text from password fields to hide validation rules
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''
        
        # Ensure password fields have proper styling
        self.fields['password1'].widget.attrs.update({
            'class': 'w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#8f3232]',
            'placeholder': 'Enter your password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#8f3232]',
            'placeholder': 'Confirm your password'
        })
    
    def save(self, commit=True):
        # Create a Customer instance instead of CustomUser
        user = super().save(commit=False)
        user.is_staff = False
        user.is_superuser = False
        user.user_type = 'customer'
        if commit:
            user.save()
        return user

class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Tailwind classes to login form fields
        self.fields['username'].widget.attrs.update({
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#8f3232]',
            'placeholder': 'Enter your username or email'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#8f3232]',
            'placeholder': 'Enter your password'
        })