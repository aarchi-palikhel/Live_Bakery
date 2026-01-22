from django import forms
from .models import ContactMessage, ContactMessageReply


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['first_name', 'last_name', 'email', 'phone', 'subject', 'message']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent text-sm sm:text-base',
                'placeholder': 'Enter your first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent text-sm sm:text-base',
                'placeholder': 'Enter your last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent text-sm sm:text-base',
                'placeholder': 'Enter your email address'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent text-sm sm:text-base',
                'placeholder': 'Enter your phone number (optional)'
            }),
            'subject': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent text-sm sm:text-base'
            }),
            'message': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent text-sm sm:text-base resize-none',
                'rows': 5,
                'placeholder': 'Enter your message here...'
            }),
        }


class ContactReplyForm(forms.ModelForm):
    send_email = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Send this reply via email to the customer"
    )
    
    class Meta:
        model = ContactMessageReply
        fields = ['reply_message']
        widgets = {
            'reply_message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Type your reply here...'
            }),
        }
        labels = {
            'reply_message': 'Your Reply',
        }


class QuickReplyForm(forms.Form):
    reply_message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Type your reply here...'
        }),
        label='Your Reply'
    )
    send_email = forms.BooleanField(
        required=False,
        initial=True,
        label='Send via email',
        help_text="Send this reply via email to the customer"
    )