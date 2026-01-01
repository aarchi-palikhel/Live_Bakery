from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from .forms import ContactForm
from products.models import Product

def home(request):
    featured_products = Product.objects.filter(
        is_featured=True, 
        available=True, 
        in_stock=True    
    )[:4]
    
    context = {
        'featured_products': featured_products,
    }
    return render(request, 'core/home.html', context)

def about(request):
    return render(request, 'core/about.html')

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        
        if form.is_valid():
            contact_message = form.save(commit=False)
            
            # Capture additional information
            if request.META.get('HTTP_X_FORWARDED_FOR'):
                contact_message.ip_address = request.META.get('HTTP_X_FORWARDED_FOR').split(',')[0]
            else:
                contact_message.ip_address = request.META.get('REMOTE_ADDR')
            
            contact_message.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            contact_message.save()
            
            # Optional: Send email notification
            try:
                if hasattr(settings, 'ADMIN_EMAIL'):
                    from django.core.mail import send_mail
                    send_mail(
                        subject=f"New Contact Message: {contact_message.get_subject_display()}",
                        message=f"""
New contact message received:

From: {contact_message.full_name}
Email: {contact_message.email}
Phone: {contact_message.phone or 'Not provided'}
Subject: {contact_message.get_subject_display()}

Message:
{contact_message.message}

IP Address: {contact_message.ip_address}
Received: {contact_message.created_at}
                        """,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[settings.ADMIN_EMAIL],
                        fail_silently=True,
                    )
            except Exception:
                # Silently fail if email sending doesn't work
                pass
            
            messages.success(request, 'Thank you for your message! We will get back to you soon.')
            return redirect('core:contact')
        
        messages.error(request, 'Please correct the errors below.')
    else:
        form = ContactForm()
    
    return render(request, 'core/contact.html', {'form': form})