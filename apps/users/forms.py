from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Customer

User = get_user_model()

class CustomerCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#8f3232]',
            'placeholder': 'Enter your email'
        })
    )
    mobile_no = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#8f3232]',
            'placeholder': 'Optional: +9779841234567'
        })
    )

    class Meta:
        model = Customer
        fields = ['username', 'email', 'mobile_no', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Tailwind classes to all fields
        for field_name, field in self.fields.items():
            if field_name not in ['email', 'mobile_no']:  # Skip already styled fields
                placeholder = f'Enter your {field.label.lower()}' if field.label else f'Enter your {field_name}'
                field.widget.attrs.update({
                    'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#8f3232]',
                    'placeholder': placeholder
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
            'placeholder': 'Enter your username'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#8f3232]',
            'placeholder': 'Enter your password'
        })