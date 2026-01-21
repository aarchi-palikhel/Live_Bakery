from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from django.apps import apps
from datetime import timedelta
import json

from .forms import ContactForm
from .models import ContactMessage


@require_http_methods(["POST"])
def clear_notification(request):
    """Clear session notification after displaying"""
    if 'notification' in request.session:
        del request.session['notification']
        request.session.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': True})


def home(request):
    """Home page with featured products"""
    from products.models import Product
    
    featured_products = Product.objects.filter(
        is_featured=True, 
        available=True, 
        in_stock=True
    ).prefetch_related('images')[:4]
    
    context = {
        'featured_products': featured_products,
    }
    return render(request, 'core/home.html', context)


def about(request):
    """About page"""
    return render(request, 'core/about.html')


def contact(request):
    """Contact form view"""
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
            except Exception as e:
                # Silently fail if email sending doesn't work
                print(f"Email sending failed: {e}")
            
            messages.success(request, 'Thank you for your message! We will get back to you soon.')
            return redirect('core:contact')
        
        messages.error(request, 'Please correct the errors below.')
    else:
        form = ContactForm()
    
    return render(request, 'core/contact.html', {'form': form})


def dashboard_callback(request, context):
    """Dashboard context callback for Unfold admin"""
    User = get_user_model()
    
    # Initialize data dictionary
    dashboard_data = {
        'users_count': User.objects.count(),
        'recent_users': User.objects.order_by('-date_joined')[:5],
    }
    
    # Safely check for Order model
    try:
        Order = apps.get_model('orders', 'Order')
        dashboard_data['orders_count'] = Order.objects.count()
        dashboard_data['pending_orders'] = Order.objects.filter(status='pending').count()
    except (LookupError, AttributeError) as e:
        print(f"Orders app not available: {e}")
        dashboard_data['orders_count'] = 0
        dashboard_data['pending_orders'] = 0
    
    # Safely check for Product model
    try:
        Product = apps.get_model('products', 'Product')
        dashboard_data['products_count'] = Product.objects.count()
    except (LookupError, AttributeError) as e:
        print(f"Products app not available: {e}")
        dashboard_data['products_count'] = 0
    
    context.update(dashboard_data)
    return context


def is_staff_or_admin(user):
    """Check if user is staff or admin"""
    return user.is_staff or user.is_superuser


@login_required
@require_http_methods(["GET"])
def dashboard_api(request):
    """
    API endpoint for dashboard data
    Returns comprehensive dashboard statistics
    Only accessible to staff and admin users
    """
    
    # Check permissions
    if not is_staff_or_admin(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        # Import models dynamically
        Order = apps.get_model('orders', 'Order')
        OrderItem = apps.get_model('orders', 'OrderItem')
        Product = apps.get_model('products', 'Product')
        
        # Date range for last 30 days
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        # 1. Total Revenue (from paid orders)
        paid_orders = Order.objects.filter(
            payment_status='paid',
            created_at__range=[start_date, end_date]
        )
        total_revenue = paid_orders.aggregate(total=Sum('total_amount'))['total'] or 0
        
        # 2. Order Statistics
        total_orders = Order.objects.filter(created_at__range=[start_date, end_date]).count()
        pending_orders = Order.objects.filter(
            status='pending',
            created_at__range=[start_date, end_date]
        ).count()
        
        # 3. Product Count
        total_products = Product.objects.filter(available=True).count()
        
        # 4. Daily Revenue (fill gaps with 0)
        daily_revenue = {}
        for order in paid_orders.order_by('created_at'):
            date_str = order.created_at.strftime('%Y-%m-%d')
            if date_str not in daily_revenue:
                daily_revenue[date_str] = 0
            daily_revenue[date_str] += float(order.total_amount)
        
        # Fill in missing dates
        current_date = start_date.date()
        while current_date <= end_date.date():
            date_str = current_date.strftime('%Y-%m-%d')
            if date_str not in daily_revenue:
                daily_revenue[date_str] = 0
            current_date = current_date + timedelta(days=1)
        
        # Sort by date
        daily_revenue = dict(sorted(daily_revenue.items()))
        
        # 5. Order Status Distribution
        order_status = {
            'pending': Order.objects.filter(status='pending', created_at__range=[start_date, end_date]).count(),
            'confirmed': Order.objects.filter(status='confirmed', created_at__range=[start_date, end_date]).count(),
            'baking': Order.objects.filter(status='baking', created_at__range=[start_date, end_date]).count(),
            'ready': Order.objects.filter(status='ready', created_at__range=[start_date, end_date]).count(),
            'completed': Order.objects.filter(status='completed', created_at__range=[start_date, end_date]).count(),
            'cancelled': Order.objects.filter(status='cancelled', created_at__range=[start_date, end_date]).count(),
        }
        
        # 6. Payment Methods
        payment_methods = {}
        if hasattr(Order, 'PAYMENT_CHOICES'):
            for payment_choice in Order.PAYMENT_CHOICES:
                count = Order.objects.filter(
                    payment_method=payment_choice[0],
                    created_at__range=[start_date, end_date]
                ).count()
                payment_methods[payment_choice[0]] = count
        else:
            payment_methods = {'cod': 0, 'esewa': 0}
        
        # 7. Delivery Types
        delivery_types = {}
        if hasattr(Order, 'DELIVERY_CHOICES'):
            for delivery_choice in Order.DELIVERY_CHOICES:
                count = Order.objects.filter(
                    delivery_type=delivery_choice[0],
                    created_at__range=[start_date, end_date]
                ).count()
                delivery_types[delivery_choice[0]] = count
        else:
            delivery_types = {'delivery': 0, 'pickup': 0}
        
        # 8. Top Products
        top_products = []
        try:
            order_items = OrderItem.objects.filter(
                order__created_at__range=[start_date, end_date]
            ).values('product__name').annotate(
                quantity_sold=Sum('quantity'),
                revenue=Sum('price')
            ).order_by('-quantity_sold')[:5]
            
            for item in order_items:
                top_products.append({
                    'product_name': item['product__name'],
                    'quantity_sold': int(item['quantity_sold'] or 0),
                    'revenue': float(item['revenue'] or 0),
                })
        except Exception as e:
            print(f"Error fetching top products: {e}")
            top_products = []
        
        # 9. Recent Orders
        recent_orders = []
        try:
            orders = Order.objects.filter(
                created_at__range=[start_date, end_date]
            ).select_related('user').order_by('-created_at')[:10]
            
            for order in orders:
                first_name = order.user.first_name or order.user.username
                last_name = order.user.last_name or ''
                initials = (first_name[0] + last_name[0]).upper() if first_name and last_name else first_name[:2].upper()
                
                recent_orders.append({
                    'order_number': getattr(order, 'order_number', f'ORD-{order.id}'),
                    'user_name': f"{first_name} {last_name}".strip(),
                    'user_initials': initials,
                    'total_amount': float(order.total_amount),
                    'status': order.status,
                    'status_display': order.get_status_display(),
                    'payment_status': order.payment_status,
                    'payment_status_display': order.get_payment_status_display(),
                    'delivery_type': order.delivery_type,
                    'created_at': order.created_at.isoformat(),
                })
        except Exception as e:
            print(f"Error fetching recent orders: {e}")
            recent_orders = []
        
        return JsonResponse({
            'total_revenue': float(total_revenue),
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'total_products': total_products,
            'daily_revenue': daily_revenue,
            'order_status': order_status,
            'payment_methods': payment_methods,
            'delivery_types': delivery_types,
            'top_products': top_products,
            'recent_orders': recent_orders,
        })
    
    except Exception as e:
        import traceback
        print(f"Dashboard API Error: {traceback.format_exc()}")
        return JsonResponse({
            'error': str(e),
            'message': 'Failed to fetch dashboard data'
        }, status=500)