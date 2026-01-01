from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import CartItem

class CartAddProductForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        max_value=20,
        initial=1,
        validators=[
            MinValueValidator(1, message="Quantity must be at least 1"),
            MaxValueValidator(20, message="Cannot add more than 20 of this item")
        ],
        widget=forms.NumberInput(attrs={
            'class': 'w-16 px-2 py-1 border border-gray-300 rounded text-center',
            'min': '1',
            'max': '20',
            'title': 'Enter quantity (1-20)'
        })
    )
    
    # Option 1: Simple BooleanField
    override = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput()
    )
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        return quantity
    
    def clean_override(self):
        # This ensures override is always a boolean
        override = self.cleaned_data.get('override')
        return bool(override)